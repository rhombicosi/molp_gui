import os


def make_dir():
    if not os.path.exists('wrkdir'):
        os.mkdir('wrkdir')


def fix_dependencies():
    from scipy.sparse.csgraph import _validation


def read_txt(path):
    text_file = open(path, "r")
    lines = text_file.readlines()
    weight_array = []

    for l in lines:
        weight_array = [float(val) for val in list(l.split(" "))]
    print(weight_array)

    text_file.close()

    return weight_array
