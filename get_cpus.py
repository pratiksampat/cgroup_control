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

        new_cores = cores
        odd_cores = False

        nodes = len(cpu_list.keys())

        if (cores % 2 != 0):
                new_cores = cores - 1
                odd_cores = True

        num_cpus_per_node = int((new_cores * threads_per_core) / nodes)
        if (cores < nodes):
                num_cpus_per_node = threads_per_core

        export_list = []
        for key in cpu_list:
                if (cores < nodes and cores <= list(cpu_list.keys()).index(key)):
                        break
                cpu_range = num_cpus_per_node
                # Compensate for the missed one core
                if odd_cores == True and key == list(cpu_list.keys())[0] and cores > nodes:
                        cpu_range += threads_per_core
                for cpus in range(int(cpu_range)):
                        export_list.append(cpu_list[key][cpus])

        export_list.sort()
        return export_list

def human_readable_cpuset(cpu_list):
        cpu_string = ""

        prev = cpu_list[0]
        cpu_string += str(prev)
        dash_used = False

        for i in range(1, len(cpu_list)):
                # print(cpu_list[i], i)
                if (cpu_list[i] == prev + 1):
                        if (dash_used == False):
                                cpu_string += "-"
                                dash_used = True
                        elif(dash_used == True and i == len(cpu_list) - 1):
                                cpu_string += str(cpu_list[i])
                else:
                        cpu_string += str(prev) + "," + str(cpu_list[i])
                        dash_used = False
                prev = cpu_list[i]

        return cpu_string


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
                print("CPUset List: ", human_readable_cpuset(cpu_list))
        else:
                print("Unable to extract CPU list")
