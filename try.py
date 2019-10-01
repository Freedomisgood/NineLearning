import numpy as np

if __name__ == "__main__":
    a=np.array([[1,2,3],[1,1,3],[1,3,3]])
    empty_list = np.where(a == 2)
    print(empty_list)