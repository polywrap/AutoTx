import json
from textwrap import dedent
import typing

import openai

class GoalResponse:
    goal: str
    type: str = "goal"

    def __init__(self, goal: str):
        self.goal = goal
    
class MissingInfoResponse:
    message: str
    type: str = "missing_info"

    def __init__(self, message: str):
        self.message = message

class InvalidPromptResponse:
    message: str
    type: str = "unsupported"

    def __init__(self, message: str):
        self.message = message

DefineGoalResponse = typing.Union[GoalResponse, MissingInfoResponse, InvalidPromptResponse]

PERSONA = dedent(
    """
    You are an AI assistant that helps you define goals and tasks for your agents. 
    You can analyze prompts and provide the user with a goal to be executed by the agents.
    When dealing with Ethereum transactions, assume you already have the address of the user.
    """
)

def build_goal(prompt: str, agents_information: str, headless: bool, strict: bool) -> str:
    response: DefineGoalResponse | None = None
    chat_history = f"User: {prompt}"

    while True:
        response = analyze_user_prompt(chat_history, agents_information)
        if response.type == "missing_info":
            autotx_message = f"Missing information: {response.message}\nInput response: "
            
            if not strict:
                return prompt

            if headless:
                raise Exception(autotx_message)
            else:
                chat_history += "\nYou: " + autotx_message + "\nUser: " + input(autotx_message)

        elif response.type == "unsupported":
            autotx_message = f"Unsupported prompt: {response.message}\nNew prompt: "
            chat_history = f"User: {input(autotx_message)}"

            if headless:
                raise Exception(autotx_message)
        elif response.type == "goal":
            return response.goal

def analyze_user_prompt(chat_history: str, agents_information: str) -> DefineGoalResponse:
    template = dedent(
        """
        Based on the following chat history between you and the user: 
        ```
        {chat_history}
        ```
            
        You must analyze the prompt and define a goal to be executed by the agents.
        If the prompt is not clear or missing information, you MUST ask for more information.
        If the prompt is invalid, unsupported or outside the scope of the agents, you MUST ask for a new prompt.
        Always ensure you have all the information needed to define the goal that can be executed without prior context.
        
        The available agents and tools:
        {agents_information}

        Respond ONLY in one of three of the following JSON formats:
        1:
        {{
            "type": "goal",
            "goal": "The detailed goal here. No need to mention specific agents or tools."
        }}
        2:
        {{
            "type": "missing_info",
            "message": "The information that is missing here"
        }}
        3:
        {{
            "type": "unsupported",
            "message": "Reason why the prompt is unsupported here"
        }}
        """
    )

    formatted_template = template.format(
        agents_information=agents_information, chat_history=chat_history
    )

    response = openai.chat.completions.create(
        model="gpt-4-turbo-preview",
        response_format={"type": "json_object"},
        messages=[
            { "role": "system", "content": PERSONA },
            { "role": "user", "content": formatted_template }
        ],
    )
    response = response.choices[0].message.content
    if not response:
        # TODO: Handle bad response
        pass

    return parse_analyze_prompt_response(response)

def parse_analyze_prompt_response(response: str) -> DefineGoalResponse:
    response = json.loads(response)
    if response["type"] == "goal":
        return GoalResponse(response["goal"])
    elif response["type"] == "missing_info":
        return MissingInfoResponse(response["message"])
    elif response["type"] == "unsupported":
        return InvalidPromptResponse(response["message"])
    else:
        raise Exception("Invalid response type")