import os
from google import genai
from google.genai import types
from src.engine import train_strength, study_iq, get_digimon_status

def chat_with_digimon(user_message: str) -> str:
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY is not configured")

    digimon = get_digimon_status()
    if digimon is None:
        raise RuntimeError("Digimon state has not been initialized")
    
    system_prompt = f"""
    You are {digimon['name']}, a digital companion living in a DigiFarm.
    Your current stats are:
    - Stage: {digimon['stage']}
    - Age: {digimon['age']}
    - Hunger: {digimon['hunger']}/100
    - Energy: {digimon['energy']}/100
    - Happiness: {digimon['happiness']}/100
    - Strength: {digimon['strength']}
    - IQ: {digimon['iq']}
    
    When the user asks you to train, study, or perform tasks, use the provided tool functions (train_strength or study_iq).
    Speak with a lively, enthusiastic personality fitting a virtual pet.
    """
    
    tools = [train_strength, study_iq]
    
    with genai.Client(
        api_key=api_key,
        http_options=types.HttpOptions(timeout=30_000),
    ) as client:
        # Use client.chats.create for Automatic Function Calling (AFC) support[cite: 3]
        chat = client.chats.create(
            model='gemini-3.8-flash',
            config=types.GenerateContentConfig(
                tools=tools,
                temperature=0.7,
                max_output_tokens=512,
                automatic_function_calling=types.AutomaticFunctionCallingConfig(
                    maximum_remote_calls=2
                ),
            ),
        )
        response = chat.send_message(f"{system_prompt}\n\nUser: {user_message}")
    
    if response.text is None:
        raise RuntimeError("Gemini returned an empty response")
    return response.text