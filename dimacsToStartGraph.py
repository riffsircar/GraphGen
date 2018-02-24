import sys

cnf_file = sys.argv[1]

with open(cnf_file) as f:
    lines = f.readlines()

edges = []
c = 0
for line in lines:
    if line[0].isalpha():
        continue
    c += 1
    edge = ""
    vs = [int(x) for x in line.split()[:-1]]
    for i in range(len(vs)):
        v = vs[i]
        if v > 0:
            edge = "V" + str(abs(v)) + " -> C" + str(c)
        else:
            edge = "C" + str(c) + " -> V" + str(abs(v))
        edges.append(edge)

print edges
