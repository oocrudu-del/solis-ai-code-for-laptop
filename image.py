import requests
import os

def generate_image_dipu(prompt):
    api_url = "https://backend.buildpicoapps.com/aero/run/image-generation-api?pk=v1-Z0FBQUFBQnBZb0Njc1JveVhVRHRrSklUWnpiY1hiTTItLWFKNjhEZWJqYmRZMzdnVGt6YjByRjBveF9EWFpubHdmZXNLbmRkUGFGZGlCaS0zMjJ5WlhSd3JoeS1KQjJvaFE9PQ=="
    print(f"Dipu AI is creating: {prompt}...")
    try:
        response = requests.post(api_url, json={"prompt": prompt})
        data = response.json()
        if data.get("status") == "success":
            image_url = data.get("imageUrl")
            img_data = requests.get(image_url).content
            file_name = "dipu_ai_image.png"
            with open(file_name, 'wb') as handler:
                handler.write(img_data)
            print(f"Image saved successfully as {file_name}!")
            os.startfile(file_name) 
            return "Hunchha baby, maile image banayera folder ma save gardiye ani open pani gardiye."
        else:
            return "Sorry, image generate huna sakena."
    except Exception as e:
        return f"Error aayo: {e}"
    
    
