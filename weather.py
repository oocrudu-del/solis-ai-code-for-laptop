# weather_gui.py

import tkinter as tk
import requests
from api import WEATHER_API_KEY as API_KEY



def show_weather(city_name_input):
    city = city_name_input.strip()
    if not city:
        print("Error: City name cannot be empty.")
        return False

    url = f"https://api.openweathermap.org/data/2.5/weather?q={city}&appid={API_KEY}&units=metric"

    try:
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            
            city_name = data["name"]
            country = data["sys"]["country"]
            temp = data["main"]["temp"]
            feels_like = data["main"]["feels_like"]
            humidity = data["main"]["humidity"]
            desc = data["weather"][0]["description"].title()
            wind = data["wind"]["speed"]
            main_weather = data["weather"][0]["main"].lower()
            
        else:
            print(f"Error: '{city}' not found or API error.")
            return False
    except Exception as e:
        print(f"Connection Error: {e}")
        return False

    # Dynamic Colors
    if "clear" in main_weather:
        bg_color = "#FF8C00"
        card_color = "#FFF8DC"
        text_color = "#8B4513"
        accent_color = "#FF4500"
    elif "rain" in main_weather or "drizzle" in main_weather or "thunderstorm" in main_weather:
        bg_color = "#2B5876"
        card_color = "#E0F7FA"
        text_color = "#006064"
        accent_color = "#0288D1"
    elif "cloud" in main_weather or "mist" in main_weather or "haze" in main_weather or "fog" in main_weather:
        bg_color = "#4A6572"
        card_color = "#F5F5F5"
        text_color = "#232F34"
        accent_color = "#34495E"
    else:
        bg_color = "#11998E"
        card_color = "#E8F5E9"
        text_color = "#1B5E20"
        accent_color = "#2E7D32"

    # GUI Build
    root = tk.Tk()
    root.title(f"Weather Report - {city_name}")
    root.geometry("400x480")
    root.configure(bg=bg_color)
    root.resizable(False, False)
    root.attributes('-alpha', 0.0)

    # Fade-in Animation
    def fade_in(alpha=0.0):
        if alpha < 1.0:
            alpha += 0.05
            root.attributes('-alpha', alpha)
            root.after(15, lambda: fade_in(alpha))

    card = tk.Frame(root, bg=card_color, bd=0)
    card.place(relx=0.08, rely=0.08, relwidth=0.84, relheight=0.84)

    labels_to_animate = []

    title_label = tk.Label(card, text="LIVE WEATHER", font=("Century Gothic", 12, "bold"), bg=card_color, fg=accent_color)
    labels_to_animate.append((title_label, "pack", {"pady": (20, 5)}))

    city_label = tk.Label(card, text=f"{city_name}, {country}", font=("Helvetica", 18, "bold"), bg=card_color, fg="#1A252C")
    labels_to_animate.append((city_label, "pack", {"pady": 5}))

    temp_label = tk.Label(card, text=f"{temp}°C", font=("Helvetica", 42, "bold"), bg=card_color, fg=bg_color)
    labels_to_animate.append((temp_label, "pack", {"pady": 5}))

    desc_label = tk.Label(card, text=f"{desc}", font=("Helvetica", 12, "italic"), bg=card_color, fg="#566573")
    labels_to_animate.append((desc_label, "pack", {"pady": (0, 15)}))

    divider = tk.Frame(card, height=2, bg=accent_color, bd=0)
    labels_to_animate.append((divider, "pack", {"fill": "x", "padx": 30, "pady": 5}))

    details_frame = tk.Frame(card, bg=card_color)
    labels_to_animate.append((details_frame, "pack", {"pady": 10}))

    feels_label = tk.Label(details_frame, text=f"🌡️ Feels Like: {feels_like}°C", font=("Helvetica", 10, "bold"), bg=card_color, fg=text_color)
    labels_to_animate.append((feels_label, "grid", {"row": 0, "column": 0, "padx": 15, "pady": 8, "sticky": "w"}))

    humidity_label = tk.Label(details_frame, text=f"💧 Humidity: {humidity}%", font=("Helvetica", 10, "bold"), bg=card_color, fg=text_color)
    labels_to_animate.append((humidity_label, "grid", {"row": 0, "column": 1, "padx": 15, "pady": 8, "sticky": "w"}))

    wind_label = tk.Label(details_frame, text=f"💨 Wind: {wind} m/s", font=("Helvetica", 10, "bold"), bg=card_color, fg=text_color)
    labels_to_animate.append((wind_label, "grid", {"row": 1, "column": 0, "columnspan": 2, "pady": 8}))

    def reveal_widgets(index=0):
        if index < len(labels_to_animate):
            widget, method, kwargs = labels_to_animate[index]
            if method == "pack":
                widget.pack(**kwargs)
            elif method == "grid":
                widget.grid(**kwargs)
            root.after(100, lambda: reveal_widgets(index + 1))

    fade_in()
    root.after(150, reveal_widgets)
    
    root.mainloop()  # यो बन्द भएपछि मात्र लुप अर्को स्टेपमा जान्छ
    return True
