import random
from eth_account import Account
from gnosis.eth import EthereumClient
from gnosis.safe import Safe, ProxyFactory
from gnosis.safe.safe_create2_tx import SafeCreate2TxBuilder
from web3.types import TxParams
from utils.cache import cache

from utils.send_tx import send_tx
from utils.constants import MASTER_COPY_ADDRESS, PROXY_FACTORY_ADDRESS

def deploy_safe_with_create2(client: EthereumClient, account: Account, signers: list[str], threshold: int) -> Safe:
    w3 = client.w3

    salt_nonce = generate_salt_nonce()
    print("Salt Nonce: ", salt_nonce)

    builder = SafeCreate2TxBuilder(
        w3=w3,
        master_copy_address=MASTER_COPY_ADDRESS,
        proxy_factory_address=PROXY_FACTORY_ADDRESS,
    )
    
    setup_data = builder._get_initial_setup_safe_data(
        owners=signers,
        threshold=threshold,
    )
    safe_address = builder.calculate_create2_address(setup_data, salt_nonce)

    # Check if safe is already deployed
    if w3.eth.get_code(safe_address) != w3.to_bytes(hexstr="0x"):
        print("Safe already deployed", safe_address)
        return Safe(safe_address, client)
    
    print("Prepared safe address: ", safe_address)

    safe_creation_tx = builder.build(
        owners=signers,
        threshold=threshold,
        salt_nonce=salt_nonce,
        gas_price=0,
    )
    
    if safe_address != safe_creation_tx.safe_address:
        raise ValueError("Create2 address mismatch")

    send_tx(
        w3,
        {
            "to": safe_creation_tx.safe_address,
            "value": safe_creation_tx.payment,
        },
        account=account,
    )

    proxy_factory = ProxyFactory(PROXY_FACTORY_ADDRESS, client)

    ethereum_tx_sent = proxy_factory.deploy_proxy_contract_with_nonce(
        account,
        MASTER_COPY_ADDRESS,
        safe_creation_tx.safe_setup_data,
        salt_nonce,
        safe_creation_tx.gas,
        w3.eth.gas_price,
    )

    print("Deploying safe address: ", safe_address)
    tx_receipt = w3.eth.wait_for_transaction_receipt(ethereum_tx_sent.tx_hash)
    if tx_receipt.status != 1:
        raise ValueError("Transaction failed")

    return Safe(safe_address, client)

def generate_salt_nonce() -> int:
    salt = cache(lambda: str(random.getrandbits(256) - 1), "./.cache/salt.txt")

    return int(salt)
