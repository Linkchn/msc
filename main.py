# This is a sample Python script.
from scipy.cluster.hierarchy import complete

from labm8 import fs

# Press ⌃R to execute it or replace it with your code.
# Press Double ⇧ to search everywhere for classes, files, tool windows, actions, and settings.




# Press the green button in the gutter to run the script.
if __name__ == '__main__':

    import clgen.clutil
    import clgen.model
    clgen.clutil.platform_info()
    import random

    uid = random.randint(0, 100000)
    fs.rm("../data/usr/{uid}".format(uid=uid))
    fs.mkdir("../data/usr/{uid}/clgen".format(uid=uid))
    fs.mkdir("../data/usr/{uid}/benchmarks".format(uid=uid))
    print("\nUnique test ID:", uid)

    print("The model used in the paper (pre-trained):")

    model = clgen.model.from_tar("../data/clgen-github-model-2016-nov-2048x3.tar.bz2")
    print(model)
    complete(model.hash == "f2fb3ad753896d54fe284c138eaa703db3518bbb",
             "Load pre-trained neural network")

