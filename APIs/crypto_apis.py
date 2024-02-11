import requests
import json
import os
from datetime import date, datetime


def convert_symbol_to_id(crypto_symbol):
    filename = "convertor.json"
    if not os.path.exists(filename):
        url = "https://api.coingecko.com/api/v3/coins/list"
        response = requests.get(url)
        convert_data = response.json()

        with open(filename, "w") as file:
            json.dump(convert_data, file)

    else:
        with open(filename, "r") as file:
            convert_data = json.load(file)

    for coin in convert_data:
        if coin['symbol'].lower() == crypto_symbol.lower():
            return coin['id']

    return None


def get_crypto_list(crypto_):
    url = "https://api.coingecko.com/api/v3/coins/list"
    response = requests.get(url)
    data = response.json()

    filename = "convertor.json"
    if not os.path.exists(filename):
        with open(filename, "w") as file:
            json.dump(data, file)

    try:
        if data["status"]["error_code"] == 429:
            with open(filename, "r") as file:
                data = json.load(file)
    except:
        pass

    crypto_list = []
    for crypto in data:
        crypto_list.append({
            "name": crypto['name'].lower(),
            "symbol": crypto['symbol'].lower(),
        })
    for crypto in crypto_list:
        if crypto_ == crypto["name"] or crypto_ == crypto["symbol"]:
            return (crypto["name"], crypto["symbol"])

    else:
        return (False, False)


# Example usage
# crypto_list = get_crypto_list()
# for crypto in crypto_list:
#     print(f"Name: {crypto['name']}\tSymbol: {crypto['symbol']}")


def get_crypto_price(crypto):
    crypto_id = convert_symbol_to_id(crypto)
    url = f"https://api.coingecko.com/api/v3/simple/price?ids={crypto_id}&vs_currencies=usd"
    response = requests.get(url)
    data = response.json()

    if crypto_id in data:
        return data[crypto_id]['usd']
    else:
        return None

# Example usage
# crypto_id = "bitcoin"
# price = get_crypto_price(crypto_id)
# if price:
#     print(f"The price of {crypto_id} is ${price}")
# else:
#     print("Failed to retrieve the cryptocurrency price.")




def get_price_range(crypto, dates):
    crypto = convert_symbol_to_id(crypto)
    dates = [datetime.strptime(date_, '%Y-%m-%d').date() for date_ in dates]
    base_url = 'https://api.coingecko.com/api/v3/coins'
    endpoint = f'{crypto}/market_chart/range'
    url = f'{base_url}/{endpoint}'

    params = {
        'vs_currency': 'usd',
        'from': int(datetime.combine(dates[0], datetime.min.time()).timestamp()),
        # datetime.datetime.min.time()).timestamp()): This parameter represents the starting point
        # of the date range for which you want to retrieve price data.
        # datetime.datetime.combine(dates[0], datetime.datetime.min.time()) combines the first
        # date from the dates list with the minimum time of the day (midnight).
        # It creates a datetime object representing the earliest possible time on that date.
        'to': int(datetime.combine(dates[-1], datetime.max.time()).timestamp())
        # datetime.datetime.max.time()).timestamp()): This parameter represents the end point
        # of the date range for which you want to retrieve price data.
        # datetime.datetime.combine(dates[-1], datetime.datetime.max.time()) combines the last
        # date from the dates list with the maximum time of the day (23:59:59).
        # It creates a datetime object representing the latest possible time on that date.
    }
    while True:
        response = requests.get(url, params=params)

        if response.status_code == 200:
            data = response.json()
            prices = data['prices']
            price_dict = {}
            empty_list = []

            for i, date in enumerate(dates):
                date_str = date.strftime('%Y-%m-%d')
                daily_prices = [price[1] for price in prices if datetime.fromtimestamp(price[0] / 1000).date() == date]
                if daily_prices:
                    price_dict[date_str] = {'min': min(daily_prices), 'max': max(daily_prices)}
                else:
                    empty_list.append(date_str)

            if price_dict:

                min_values = [item["min"] for item in price_dict.values()]
                mean_min = sum(min_values) / len(min_values)
                max_values = [item["max"] for item in price_dict.values()]
                mean_max = sum(min_values) / len(max_values)
                for date in empty_list:
                    price_dict[date] = {'min': mean_min, 'max': mean_max}

                return price_dict



if __name__ == "__main__":
    crypto = 'bitcoin'
    dates = ["2023-6-26", "2023-6-29", "2023-6-30"]

    price_range = get_price_range(crypto, dates)
    print(price_range)
