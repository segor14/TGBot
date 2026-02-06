import requests as rq
from datetime import datetime
import matplotlib.pyplot as plt

def get_real_temp(CITY, API_KEY):
    url = f"http://api.openweathermap.org/data/2.5/weather?q={CITY}&appid={API_KEY}&units=metric"
    response = rq.get(url)
    if response.status_code == 200:
        data = response.json()
        return data['main']['temp']
    elif response.status_code == 401:
        return '401'
    else:
        raise ValueError('Ошибка при запросе данных')
    
def get_API_key(path='api.txt'):
    with open(path, 'r') as file:
        api = file.readline()
        return api.strip()

def get_food_info(product_name):
    url = f"https://world.openfoodfacts.org/cgi/search.pl?action=process&search_terms={product_name}&json=true"
    response = rq.get(url)
    if response.status_code == 200:
        data = response.json()
        products = data.get('products', [])
        if products:  # Проверяем, есть ли найденные продукты
            first_product = products[0]
            return {
                'name': first_product.get('product_name', 'Неизвестно'),
                'calories': first_product.get('nutriments', {}).get('energy-kcal_100g', 0)
            }
        return None
    return None

def count_water(weight, active_time, city):
    api = get_API_key()
    temperature = get_real_temp(city, api)
    return weight * 30 + 500 * (active_time / 30) + 500 * (20 / temperature)

def count_calorie(sex, weight, height, age, active_time):
    if sex == 'man':
        BMR = 10 * weight + 6.25 * height - 5 * age + 5
    else:
        BMR = 10 * weight + 6.25 * height - 5 * age - 161

    kcal_per_min = BMR / 1440  # 24 * 60
    activity_met = 5  # умеренная активность (пример)

    activity_calories = kcal_per_min * activity_met * active_time

    return BMR + activity_calories

def get_today_date():
    return datetime.now().strftime("%Y-%m-%d")

def plot_stat(user_id, amount_mass, time_mass):
    times = []
    cum_sum = []
    
    total = 0
    for i in range(len(amount_mass)):
        total += amount_mass[i]
        times.append(datetime.fromisoformat(time_mass[i]))
        cum_sum.append(total)

    plt.figure(figsize=(8, 4))
    plt.plot(times, cum_sum)
    plt.xlabel("Время")
    plt.ylabel("Выпито воды (мл)")
    plt.title("Потребление воды за день")
    plt.grid(True)

    path = f"water_{user_id}.png"
    plt.tight_layout()
    plt.savefig(path)
    plt.close()

    return path