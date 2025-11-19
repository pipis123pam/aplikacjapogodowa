from kivy.metrics import dp
from kivy.animation import Animation
from kivy.clock import mainthread
from kivy.uix.boxlayout import BoxLayout
from kivy.properties import StringProperty, DictProperty, NumericProperty, ListProperty
from kivy.network.urlrequest import UrlRequest
from kivymd.app import MDApp
from kivymd.uix.card import MDCard
from kivymd.uix.label import MDLabel
from kivymd.uix.button import MDIconButton, MDButton 
from kivymd.uix.menu import MDDropdownMenu
from datetime import datetime, timedelta

BASE_URL = "https://dollars-analysts-broadband-height.trycloudflare.com/weather"

DAYS = ["Poniedziałek", "Wtorek", "Środa", "Czwartek", "Piątek", "Sobota", "Niedziela"]

WOJEWODZTWA = [
    "Dolnośląskie", "Kujawsko-Pomorskie", "Lubelskie", "Lubuskie", 
    "Łódzkie", "Małopolskie", "Mazowieckie", "Opolskie", 
    "Podkarpackie", "Podlaskie", "Pomorskie", "Śląskie", 
    "Świętokrzyskie", "Warmińsko-Mazurskie", "Wielkopolskie", "Zachodniopomorskie"
]

class WeatherRoot(BoxLayout):
    pass

class DayCard(MDCard):
    day_index = NumericProperty(0)
    day_label = StringProperty("")
    date_label = StringProperty("")
    place = StringProperty("")
    raw_data = DictProperty({})
    selected_hour = NumericProperty(1)
    icons = ListProperty(["thermometer", "speedometer", "weather-rain"])

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.size_hint_y = None
        self.height = dp(260)
        self.radius = [18]
        self.padding = dp(10)
    
    def on_selected_hour(self, instance, value):
        self.update_values_from_raw()
        
    @mainthread
    def update_values_from_raw(self):
        try:
            hours = self.raw_data.get("hour", [])
            temps = self.raw_data.get("temperature", [])
            wind = self.raw_data.get("wind", [])
            prec = self.raw_data.get("precipitation", []) or self.raw_data.get("shower", [])
            
            if not hours:
                hour_text = "--"
                temp_text = "-- °C"
                wind_text = "-- km/h"
                prec_text = "-- mm"
            else:
                target = int(self.selected_hour)
                idx = 0
                if len(hours) >= 24:
                    idx = max(0, min(len(hours)-1, target-1))
                else:
                    diffs = [abs((h if isinstance(h,int) else int(h)) - target) for h in hours]
                    idx = diffs.index(min(diffs))

                hour_text = str(hours[idx])
                temp_text = f"{temps[idx]} °C" if idx < len(temps) else "-- °C"
                wind_text = f"{wind[idx]} km/h" if idx < len(wind) else "-- km/h"
                prec_text = f"{prec[idx]} mm" if idx < len(prec) else "-- mm"

            
            if hasattr(self, "ids"):
                if "hour_val" in self.ids:
                    self.ids.hour_val.text = f"Godzina: {hour_text}"
                if "temp_val" in self.ids:
                    self.ids.temp_val.text = f"Temperatura: {temp_text}"
                if "press_val" in self.ids:
                    self.ids.press_val.text = f"Wiatr: {wind_text}"
                if "prec_val" in self.ids:
                    self.ids.prec_val.text = f"Opady: {prec_text}"
        except Exception as e:
            print("update_values_from_raw error:", e)


class WeatherApp(MDApp):
    selected_wojewodztwo = StringProperty("Wybierz Województwo")
    menu = None

    def build(self):
        self.theme_cls.theme_style = "Dark"
        self.theme_cls.primary_palette = "Red"
        return WeatherRoot()
    
    def open_wojewodztwa_menu(self, button):
        if not self.menu:
            menu_items = [
                {
                    "text": woj,
                    "on_release": lambda x=woj: self.set_wojewodztwo(x)
                } 
                for woj in WOJEWODZTWA
            ]
            
            self.menu = MDDropdownMenu(
                caller=button, 
                items=menu_items, 
                width_mult=4
            )
        
        self.menu.open()

    def set_wojewodztwo(self, wojewodztwo):
        self.selected_wojewodztwo = wojewodztwo
        self.menu.dismiss()
        
    def on_start(self):
        root = self.root
        welcome = root.ids.welcome_box
        Animation(opacity=1, d=0.8, t="out_quad").start(welcome)
        
    def on_search(self, text):
        place = text.strip()
        if not place:
            return
        container = self.root.ids.content_container
        container.clear_widgets()
        
        
        header = MDLabel(text=f"Prognoza dla: [b]{place}[/b]", 
                         halign="center", markup=True, role="small", size_hint_y=None, height=dp(40))
        container.add_widget(header)

        CARD_COLORS = [
            (0.12, 0.02, 0.02, 1),
            (0.02, 0.08, 0.08, 1), 
            (0.08, 0.02, 0.08, 1), 
            (0.08, 0.08, 0.02, 1), 
            (0.02, 0.02, 0.08, 1), 
            (0.05, 0.05, 0.05, 1), 
            (0.1, 0.05, 0.0, 1)    
        ]
        
        for i in range(7):
            data_day = datetime.now() + timedelta(days=i)
            day_label = DAYS[data_day.weekday()]
            date_label = data_day.strftime("%d.%m")
            
            card_color = CARD_COLORS[i % len(CARD_COLORS)]

            
            card = DayCard(
                day_index=i, 
                day_label=day_label, 
                date_label=date_label, 
                place=place, 
                md_bg_color=card_color 
            )
            container.add_widget(card)
            self.fetch_day_data(place, i, card)

    def fetch_day_data(self, place, day_index, card_widget: DayCard):
        endpoints = [
            "weather",
            "weatherdaytwo",
            "weatherdaythree",
            "weatherdayfour",
            "weatherdayfive",
            "weatherdaysix",
            "weatherdayseven"
        ]
        if day_index < len(endpoints):
            endpoint = endpoints[day_index]
        else:
            endpoint = "weather"
            
        url = f"{BASE_URL}/{endpoint}?place={place}"
        
        def success(req, result):
            card_widget.raw_data = result
            card_widget.selected_hour = 1 
            
            try:
                if hasattr(card_widget, "ids") and "hour_slider" in card_widget.ids:
                    card_widget.ids.hour_slider.min = 1
                    card_widget.ids.hour_slider.max = 24
                    card_widget.ids.hour_slider.value = 1
            except Exception:
                pass
            card_widget.update_values_from_raw() 


        def fail(req, result):
            print(f"Błąd pobierania dla {url}:", result)
            card_widget.raw_data = {}
            card_widget.update_values_from_raw()

        
        try:
            UrlRequest(url, on_success=lambda req, res: success(req, res),
                       on_failure=lambda req, res: fail(req, res),
                       on_error=lambda req, err: fail(req, err),
                       timeout=15)
        except Exception as e:
            print("fetch_day_data exception:", e)
            card_widget.raw_data = {}
            card_widget.update_values_from_raw()

    def reload_app(self):
        root = self.root
        container = root.ids.content_container
        container.clear_widgets()
        root.ids.welcome_box.opacity = 1
        root.ids.search_field.text = ""
        self.selected_wojewodztwo = "Wybierz Województwo"

if __name__ == "__main__":
    WeatherApp().run()