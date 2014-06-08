import requests

pubmintapi = 'https://api.mintpal.com/v1/market'
pubkrakapi = 'https://api.kraken.com/0/public'


def get_cur_price(f, t):
    u = '{0}/stats/{1}/{2}'.format(pubmintapi, f, t)
    r = requests.get(u)

    if r.status_code == 200:
        j = r.json()
        return j[0]['last_price']
    return False


def btc_to_eur():
    pair = 'XXBTZEUR'
    u = '{0}/Ticker?pair={1}'.format(pubkrakapi, pair)
    r = requests.get(u)

    if r.status_code == 200:
        ret = r.json()
        return ret['result'][pair]['c'][0]
    return False


def reply(args):
    if len(args) < 2 or len(args[1]) > 5:
        return 'usage: coin <currency> [amount]'

    e = btc_to_eur()  # get current EUR price for 1 BTC
    c = get_cur_price(args[1], 'BTC')  # get current BTC price for currency

    if e is False or c is False:
        return 'nope.'

    ratio = float(c) * float(e)  # get currency value in EUR

    rep = '1 BTC -> {0} EUR / 1 {1} -> {2} BTC / 1 {1} -> {3} EUR'
    rep = rep.format(e, args[1], c, ratio)

    if len(args) > 2 and len(args[2]) < 20:
        try:
            val = int(args[2]) * ratio
            rep = rep + ' / {0} {1} -> {2} EUR'.format(args[2], args[1], val)
        except ValueError:
            pass

    return rep
