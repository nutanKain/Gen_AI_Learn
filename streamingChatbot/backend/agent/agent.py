from openai import AzureOpenAI
from config.config import api_key, api_base, api_version
from fastapi import Request
openai=AzureOpenAI(api_key=api_key,
azure_endpoint=api_base,
api_version=api_version
)

async def chatbot(user_prompt:str, request: Request):
    """
    Generator function that yields a stream of resposnes in real time from model.
    """
    messages=[
        {"role":"system", "content": "You are a helpful, concise, and friendly AI assistant. Answer clearly and directly."},
        {"role":"user","content": user_prompt}
    ]

    response=openai.chat.completions.create(
        stream=True, #stream the response in real time
        model="gpt-4.1",
        messages=messages,
        max_tokens=100,

        # max_completion_tokens=32768 , #32,768  tokens is the maximum for the gpt-4.1 model to generate tokens in a singe response
        temperature=0.5, #controls randomness/creativity (0.0 TO 2.0) , ADJUSTS THE DETERINNSTICITY OF THE RESPONSE
        top_p=1.0, #controls the diversity of the response (0.0 TO 1.0) , ADJUSTS THE DIVERSITY OF THE RESPONSE 1.0 means considers all tokns, 0.9 means it considers few top tokens whole strength is almost 90%
        frequency_penalty=0.5, #controls the frequency of the  or words (0.0 TO 1.0). eg User: "Tell me about Python" Model: "Python is a programming language. Python is versatile. Python can be used for many things. Python is popular. Python is easy to learn." , ADJUSTS THE FREQUENCY OF THE RESPONSE 1.0 means penalizes frequent tokens, 0.9 means it penalizes less frequent tokens
        presence_penalty=0.5, #controls the presence of the or words (0.0 TO 1.0). eg User: "Tell me about Python" Model: "Python is a programming language. Python is versatile. Python can be used for many things. Python is popular. Python is easy to learn." , ADJUSTS THE PRESENCE OF THE RESPONSE 1.0 means penalizes less presence of tokens, 0.9 means it penalizes more presence of tokens
    )
    
    try:
        # full_response = ""

        # print(response.choices[0].message.content)
        #when we use stream=True, we need to print the response in real time
        # Handle streaming response
        
        for chunk in response:
            if await request.is_disconnected():
                  print("Client disconnected, stopping stream")
                  break  


            if chunk.choices and chunk.choices[0].delta.content:
                token=chunk.choices[0].delta.content
                #SSE format
                yield f"data: {token}\n\n"
        
        #signal cpmpletion
        yield "data: [DONE]\n\n"
    
    except Exception as e:
        yield f"data: [ERROR] {str(e)}\n\n"

