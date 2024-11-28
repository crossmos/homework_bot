
class APIStatusError(Exception):

    def __str__(self):
        return (
            'Ошибка запроса.'
            f'Статус-код: {response.status_code}. '
            f'Адрес запроса: {response.url}'
            f'Параметры ответа: {response.request}'
        )
