import pytest
from sage_agent.utils.ethereum import (
    SafeManager,
)
from sage_agent.utils.ethereum.uniswap.swap import build_swap_transaction
from sage_agent.utils.configuration import get_configuration
from sage_agent.utils.ethereum.helpers.show_balances import (
    show_address_balances,
    weth_address,
    usdc_address,
    dai_address,
    wbtc_address,
)


@pytest.mark.skip()
def test_swap(configuration):
    (user, _, client, _) = configuration

    show_address_balances(client.w3, user.address)

    txs = build_swap_transaction(
        client, 0.05, wbtc_address, usdc_address, user.address, True
    )

    for i, tx in enumerate(txs):
        transaction = user.sign_transaction(
            {
                **tx,
                "nonce": client.w3.eth.get_transaction_count(user.address),
                "gas": 150000,
            }
        )

        hash = client.w3.eth.send_raw_transaction(transaction.rawTransaction)

        receipt = client.w3.eth.wait_for_transaction_receipt(hash)

        if receipt["status"] == 0:
            print(f"Transaction #{i} failed ")
            break

    show_address_balances(client.w3, user.address)


@pytest.mark.skip()
def test_swap_through_safe():
    (user, agent, client) = get_configuration()
    manager = SafeManager.deploy_safe(
        client, user, agent, [user.address, agent.address], 1
    )

    show_address_balances(client.w3, user.address)

    txs = build_swap_transaction(
        client, 5000, dai_address, usdc_address, manager.address, True
    )

    hash = manager.send_multisend_tx(txs)
    manager.wait(hash)

    show_address_balances(client.w3, user.address)