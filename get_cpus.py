import argparse
import psutil
import os

SYS_PATH = "/sys/devices/system"
NODE_PATH = SYS_PATH + "/node"

def get_cpus(cores):
        ## Read through the directory structure to see how many nodes exist and populate for CPUs
        cpu_list = {}
        nodes = 0

        threads_per_core = psutil.cpu_count() / psutil.cpu_count(logical=False)

        if (cores * threads_per_core > psutil.cpu_count()):
                print("Invalid core count..")
                return -1

        directory = os.fsencode(NODE_PATH)
        for file in os.listdir(directory):
                f = os.fsdecode(file)
                node_name = NODE_PATH + "/" + f
                if f.startswith("node") and os.path.isdir(node_name):
                        node = f.partition("node")
                        # word[2] because we want the keyword after our string
                        cpu_list[int(node[2])] = []
                        for cpu_file in os.listdir(node_name):
                                c = os.fsdecode(cpu_file)
                                cpu_name = node_name + "/" + c
                                if c.startswith("cpu") and os.path.isdir(cpu_name):
                                        # Try block only for those cpus that do not
                                        # have an online_file like CPU 0
                                        try:
                                                online_file = open(cpu_name + "/online")
                                                content = int(online_file.read().strip())
                                                if (content == 0):
                                                        continue
                                        except:
                                                pass
                                        cpu = c.partition("cpu")
                                        cpu_list[int(node[2])].append(int(cpu[2]));

        cpus_per_node = []

        for key in cpu_list:
                cpus_per_node.append(len(cpu_list[key]))
                cpu_list[key].sort()

        nodes = len(cpu_list.keys())
        cpus_per_node = int((cores * threads_per_core) / nodes)

        export_list = []
        for key in cpu_list:
                for cpus in range(cpus_per_node):
                        export_list.append(cpu_list[key][cpus])
                        
        return export_list

def parse_args():
        parser = argparse.ArgumentParser()
        parser.add_argument("--cores", "-c", help="num of cpus needed, split between nodes default: 2",
                            default=2, type=int)
        args = parser.parse_args()
        return args

if __name__=="__main__":
        args = parse_args()
        cpu_list = get_cpus(args.cores)
        if (cpu_list != -1):
                cpu_string = ','.join(map(str, cpu_list))
        print(cpu_string)