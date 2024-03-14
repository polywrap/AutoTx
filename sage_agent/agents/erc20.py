from langchain_core.tools import tool
from crewai import Agent
from sage_agent.utils.agents_config import AgentConfig, agents_config
from sage_agent.utils.ethereum import (
    build_transfer_erc20,
    get_erc20_balance,
)
from sage_agent.utils.ethereum import load_w3
from sage_agent.utils.llm import open_ai_llm
from sage_agent.utils.ethereum.config import contracts_config
from sage_agent.sage import transactions


@tool("Prepare transfer transaction")
def prepare_transfer_transaction(amount: float, reciever: str, token: str):
    """
    Prepares a transfer transaction for given amount in decimals for given token

    Args:
        amount (float): Amount given by the user to transfer. The function will take
        care of converting the amount to needed decimals.
        reciever (str): The address of reciever
        token (str): Symbol of token to transfer
    Returns:
        Transaction object with filled data to execute transfer
    """
    tokens = contracts_config["erc20"]
    token_address = tokens[token.lower()]
    tx = build_transfer_erc20(load_w3(), token_address, reciever, amount)

    transactions.append(tx)

    return tx


@tool("Check owner balance in ERC20 token")
def get_balance(token: str, owner: str):
    """
    Check balance of given owner in ERC20 contract

    :param token: str, token symbol of erc20
    :param owner: str, address of owner of tokens

    :result balance: int, the balance of owner in erc20 contract
    """
    tokens = contracts_config["erc20"]
    token_address = tokens[token.lower()]
    
    return get_erc20_balance(load_w3(), token_address, owner)


class Erc20Agent(Agent):
    name: str

    def __init__(self):
        name = "erc20"
        config: AgentConfig = agents_config[name].model_dump()
        super().__init__(
            **config,
            tools=[
                prepare_transfer_transaction,
                get_balance,
            ],
            llm=open_ai_llm,
            verbose=True,
            allow_delegation=False,
            name=name,
        )
