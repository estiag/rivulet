import json


def format_json(inputs):
    if isinstance(inputs, str):
        return json.dumps(json.loads(inputs), indent=4, ensure_ascii=False)
    else:
        return json.dumps(inputs, indent=4, ensure_ascii=False)


if __name__ == '__main__':
    print(format_json('{"test":2}'))
    print(format_json({'a': 1}))
