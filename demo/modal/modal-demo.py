import modal

app = modal.App()


@app.function(gpu="any", cpu=8.0, memory=32768)
def my_func(a):
    if a == 2:
        raise Exception("ohno")
    return a ** 2

@app.local_entrypoint()
def main():
    print(list(my_func.map(range(1), return_exceptions=True)))
    # [0, 1, UserCodeException(Exception('ohno'))]
