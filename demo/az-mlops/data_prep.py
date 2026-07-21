# import pandas as pd
# from sklearn.datasets import load_iris

# # Save dataset as CSV
# def main():
#     X, y = load_iris(return_X_y=True, as_frame=True)
#     df = X.copy()
#     df["target"] = y
#     df.to_csv("iris.csv", index=False)

# if __name__ == "__main__":
#     main()


import pandas as pd
from sklearn.datasets import load_iris

# Save dataset as CSV
def main():
    X, y = load_iris(return_X_y=True, as_frame=True)
    df = X.copy()
    df["target"] = y
    df.to_csv("iris.csv", index=False)

if __name__ == "__main__":
    main()
