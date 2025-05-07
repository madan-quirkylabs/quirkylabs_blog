from vertexai.preview.language_models import ChatModel
import vertexai
from langchain_core.prompts import ChatPromptTemplate
from langchain_google_vertexai import ChatVertexAI

system = "You are a helpful assistant who translate English to French"
human = "Translate this sentence from English to French. I love programming."
prompt = ChatPromptTemplate.from_messages([("system", system), ("human", human)])

chat = ChatVertexAI(model="gemini-2.0-flash", convert_system_message_to_human=True)

chain = prompt | chat
print(chain.invoke({}))
