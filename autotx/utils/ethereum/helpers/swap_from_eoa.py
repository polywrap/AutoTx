from decimal import Decimal
from autotx.utils.ethereum.eth_address import ETHAddress
from eth_account.signers.local import LocalAccount
from gnosis.eth import EthereumClient
from autotx.utils.ethereum.lifi.swap import build_swap_transaction
from autotx.utils.ethereum.networks import ChainId


def swap(
    client: EthereumClient,
    user: LocalAccount,
    amount: float,
    from_token: ETHAddress,
    to_token: ETHAddress,
    chain: ChainId,
) -> None:
    txs = build_swap_transaction(
        client,
        Decimal(amount),
        from_token,
        to_token,
        ETHAddress(user.address),
        False,
        chain,
    )

    for i, tx in enumerate(txs):
        transaction = user.sign_transaction(  # type: ignore
            {
                **tx.tx,
                "nonce": client.w3.eth.get_transaction_count(user.address)
            }
        )

        hash = client.w3.eth.send_raw_transaction(transaction.rawTransaction)

        receipt = client.w3.eth.wait_for_transaction_receipt(hash)

        if receipt["status"] == 0:
            print(f"Transaction #{i} failed ")
            break
