import os
import google.generativeai as genai

genai.configure(api_key="AIzaSyAt-9E4d9zBwkOUsUHLTGGseLKbkuXp7zM")
model = genai.GenerativeModel('gemini-3.5-flash')
response = model.generate_content("안녕! 잘 작동하니?")
print(response.text)