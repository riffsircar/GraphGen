import sys
file_name = sys.argv[1]
cnf_file = sys.argv[2]
rules_file = sys.argv[3]

def dimacsToStartGraph(cnf_file):
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
        for v in vs:
            edge = "V" + str(abs(v)) + " -> C" + str(c)
            edges.append(edge)
    return edges

def getRules(rules_file):
    with open(rules_file) as f:
        lines = f.readlines()
    lines_rev = []
    for line in lines:
        id1 = line.index('==>')
        id2 = id1 + 4
        id3 = line.index(';')
        lhs = line[:id1-1]
        rhs = line[id2:id3]
        lines_rev.append(rhs + ' ==> ' + lhs + ';\n')
    
    return lines_rev

output_filename = file_name + ".txt"
output_file = open(output_filename, "w")
start_graph = ""
edges = dimacsToStartGraph(cnf_file)
print edges
for e in edges:
    start_graph += e + ", "
start_graph = start_graph[:-2] + ";"
    
output = "productions {\n"
output += "# Start graph\n"
output += start_graph
output += "\n\n# Rules\n"
rules = getRules(rules_file)
for rule in rules:
    output += rule
output += "\n}"
output_file.write(output)
output_file.close()
