from textwrap import dedent
from typing import Callable
from crewai import Agent
from pydantic import Field
from autotx.AutoTx import AutoTx
from autotx.auto_tx_agent import AutoTxAgent
from autotx.auto_tx_tool import AutoTxTool
from autotx.utils.ethereum.eth_address import ETHAddress
from autotx.utils.ethereum.networks import NetworkInfo
from autotx.utils.ethereum.uniswap.swap import SUPPORTED_UNISWAP_V3_NETWORKS, build_swap_transaction
from gnosis.eth import EthereumClient, EthereumNetworkNotSupported, EthereumNetwork


def get_tokens_address(token_in: str, token_out: str, network_info: NetworkInfo):
    token_in = token_in.lower()
    token_out = token_out.lower()

    if not network_info.network in SUPPORTED_UNISWAP_V3_NETWORKS:
        raise EthereumNetworkNotSupported(
            f"Network with chain id {network_info.network.value} not supported for swap"
        )

    if token_in not in network_info.tokens:
        raise Exception(f"Token {token_in} is not supported")

    if token_out not in network_info.tokens:
        raise Exception(f"Token {token_out} is not supported")

    return (network_info.tokens[token_in], network_info.tokens[token_out])


class ExecuteSwapExactInTool(AutoTxTool):
    name: str = "Prepare needed transactions to execute swap with exact input"
    description: str = dedent(
        """
        Encodes approve, if necessary and swap transactions. The function will only add the approve transaction
        if the address does not have enough allowance

        Args:
            exact_amount_in (float): Amount of token_in given by the user to trade. The function will take care of converting the amount
            to needed decimals.
            token_in (str): Symbol of token input.
            token_out (str): Symbol of token output.
        Returns:
            str: A confirmation message that the transaction to swap tokens has been prepared
        """
    )
    recipient: ETHAddress | None = Field(None)
    client: EthereumClient | None = Field(None)

    def __init__(self, autotx: AutoTx, client: EthereumClient, recipient: ETHAddress):
        super().__init__(autotx)
        self.client = client
        self.recipient = recipient

    def _run(self, exact_amount_in: float, token_in: str, token_out: str) -> str:
        (token_in_address, token_out_address) = get_tokens_address(
            token_in, token_out, self.autotx.network
        )

        swap_transactions = build_swap_transaction(
            self.client,
            exact_amount_in,
            token_in_address,
            token_out_address,
            self.recipient.hex,
            True,
        )
        self.autotx.transactions.extend(swap_transactions)

        return f"Transaction to sell {exact_amount_in} {token_in} for {token_out} has been prepared"

class ExecuteSwapExactOutTool(AutoTxTool):
    name: str = "Prepare needed transactions to execute swap with exact output"
    description: str = dedent(
        """
        Encodes approve, if necessary and swap transactions. The function will only add the approve transaction
        if the address does not have enough allowance

        Args:
            exact_amount_out (float): Amount of token_out given by the user to trade. The function will take care of converting the amount
            to needed decimals.
            token_in (str): Symbol of token input.
            token_out (str): Symbol of token output.
        Returns:
            str: A confirmation message that the transaction to swap tokens has been prepared
        """
    )
    recipient: ETHAddress | None = Field(None)
    client: EthereumClient | None = Field(None)

    def __init__(self, autotx: AutoTx, client: EthereumClient, recipient: ETHAddress):
        super().__init__(autotx)
        self.client = client
        self.recipient = recipient

    def _run(self, exact_amount_out: float, token_in: str, token_out: str) -> str:
        (token_in_address, token_out_address) = get_tokens_address(
            token_in, token_out, self.autotx.network
        )

        swap_transactions = build_swap_transaction(
            self.client,
            exact_amount_out,
            token_in_address,
            token_out_address,
            self.recipient.hex,
            False,
        )
        self.autotx.transactions.extend(swap_transactions)

        return f"Transaction to buy {exact_amount_out} {token_out} with {token_in} has been prepared"


class SwapTokensAgent(AutoTxAgent):
    def __init__(self, autotx: AutoTx, client: EthereumClient, recipient: ETHAddress):
        super().__init__(
            name="swap-tokens",
            role="Expert in swapping tokens",
            goal=f"Perform token swaps, manage liquidity, and query pool statistics on the Uniswap protocol (address: {autotx.manager.address})",
            backstory="An autonomous agent skilled in Ethereum blockchain interactions, specifically tailored for the Uniswap V3 protocol.",
            tools=[
                ExecuteSwapExactInTool(autotx, client, recipient),
                ExecuteSwapExactOutTool(autotx, client, recipient),
            ],
        )


def build_agent_factory(
    client: EthereumClient, recipient: ETHAddress
) -> Callable[[AutoTx], Agent]:
    def agent_factory(autotx: AutoTx) -> SwapTokensAgent:
        return SwapTokensAgent(autotx, client, recipient)

    return agent_factory
