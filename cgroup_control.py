'''
Experimental and early version script to control create and limit CPU and
CPUset controllers as well as spawn tasks in those cgroups

Note: The script must be run as root

Instructions to run:
# ./cgroup_control.py \
        --controllers <controlers comma seperated>\
        --cpuset="<cpuset>"\
        --period=<integer> --quota=<integer> \
        "<command in quotes>"

Example
# ./cgroup_control.py \
        --controllers cpuset,cpu\
        --cpuset="0-3"\
        --period=100000 --quota=30000 \
        "cat /dev/random > /dev/null"
This will create two controllers cpuset and cpu.
Cpuset restrited cpus 0-3.
Cpu controller restricted with period=100000us and quota=30000
The cgroup will be called my_group as that is the default

TODO:
Currently limits are set manually. Add test scenarios which detect the
system configuration and can configure limits automatically

@Author: Pratik R. Sampat, IBM Corp
'''

from pathlib import Path
import argparse
import psutil
import os
import subprocess
import get_cpus
import multiprocessing
from time import sleep

cgroupfs = "/sys/fs/cgroup/"

def create_cgroupv1_heir(controllers, cgroup_name):
        try:
                for folder in controllers:
                        Path(cgroupfs+folder+"/"+cgroup_name).mkdir(parents=True, exist_ok=True)
                        if (not Path(cgroupfs+folder+"/"+cgroup_name+"/tasks").is_file()):
                                print("Creation of cgroup failed. Exiting...")
                                exit(1)

        except:
                print("Creation of cgroup failed. Exiting...")
                exit(1)

def create_cgroupv2_heir(controllers, cgroup_name):
        try: 
                file = open(cgroupfs+"cgroup.subtree_control", "a")
                ctrls = ""
                for c in controllers:
                        ctrls += "+"+c+" "
                file.write(ctrls)
                file.close()
                Path(cgroupfs+cgroup_name).mkdir(parents=True, exist_ok=True)

                # Check if the controllers are populated correctly
                file = open(cgroupfs+cgroup_name+"/cgroup.controllers", "r")
                avail_ctrls = file.read().split()
                file.close()
                if (not set(controllers).issubset(set(avail_ctrls))):
                        print("Controllers not set correctly. Exiting...")
                        exit(1)
        except:
                print("Creation of cgroup failed. Exiting...")
                exit(1)

def create_cgroup_heir(cgroup_ver, controllers, cgroup_name, nolibcgroup):
        try:
                if (nolibcgroup == True):
                        raise Exception("No libcgroup. Use traditional interface") 
                command = "cgcreate"
                for c in controllers:
                        command += " -g " + c + ":" + cgroup_name
                if os.system(command) != 0:
                         raise Exception("failed: ", command) 
        except:
                if (cgroup_ver == 1):
                        create_cgroupv1_heir(controllers, cgroup_name)
                else:
                        create_cgroupv2_heir(controllers, cgroup_name)

def populate_v1_limits(args, nodes_str):
        try:
                if ("cpuset" in args.controllers):
                        file = open(cgroupfs+"/cpuset/"+args.cgroup_name+"/cpuset.cpus", "w")
                        file.write(args.cpuset)
                        file.close()

                        file = open(cgroupfs+"/cpuset/"+args.cgroup_name+"/cpuset.mems", "w")
                        file.write(nodes_str)
                        file.close()
                if ("cpu" in args.controllers):
                        file = open(cgroupfs+"/cpu/"+args.cgroup_name+"/cpu.cfs_period_us", "w")
                        file.write(str(args.period))
                        file.close()

                        file = open(cgroupfs+"/cpu/"+args.cgroup_name+"/cpu.cfs_quota_us", "w")
                        file.write(str(args.quota))
                        file.close()
        except:
                print("Limits cannot be set. Exiting...")
                exit(1)

def populate_v2_limits(args, nodes_str):
        try:
                if ("cpuset" in args.controllers):
                        file = open(cgroupfs+args.cgroup_name+"/cpuset.cpus", "w")
                        file.write(args.cpuset)
                        file.close()
                if ("cpu" in args.controllers):
                        file = open(cgroupfs+args.cgroup_name+"/cpu.max", "w")
                        limit = ""
                        if (args.quota == -1):
                                limit += "max"
                        else:
                                limit += str(args.quota)
                        limit += " " + str(args.period)
                        file.write(limit)
                        file.close()
        except:
                print("Limits cannot be set. Exiting...")
                exit(1)


def populate_cgroup_limits(cgroup_ver, args):
        nodes_list = get_cpus.get_nodes()
        nodes_str = ','.join(str(e) for e in nodes_list)
        try:
                if (args.nolibcgroup == True):
                        raise Exception("No libcgroup. Use traditional interface")
                command = "cgset"
                if ("cpuset" in args.controllers):
                        command += " -r cpuset.cpus=" + str(args.cpuset)
                        command += " -r cpuset.mems=" + nodes_str
                if ("cpu" in args.controllers):
                        if (cgroup_ver == 1):
                                command += " -r cpu.cfs_period_us=" + str(args.period)
                                command += " -r cpu.cfs_quota_us=" +str(args.quota)
                        else:
                                limit = "'"
                                if (args.quota == -1):
                                        limit += "max"
                                else:
                                        limit += str(args.quota)
                                limit += " " + str(args.period)
                                limit += "'"

                                command += " -r cpu.max=" + limit

                command += " " + args.cgroup_name
                if os.system(command) != 0:
                         raise Exception("failed: ", command) 
        except:
                if (cgroup_ver == 1):
                        populate_v1_limits(args, nodes_str)
                else:
                        populate_v2_limits(args, nodes_str)

# Write the current process's pid to the controller so that the child
# is always spawned in it
def execute_v1_command(controllers, cgroup_name, program):
        try:
                for c in controllers:
                        file = open(cgroupfs+c+"/"+cgroup_name+"/tasks", "a")
                        file.write(str(os.getpid()))
                        file.close()
                if (subprocess.call(program, shell=True) != 0):
                        raise Exception("failed: ", program)
        except KeyboardInterrupt:
                print("Keyboard interrupt. Exiting...")
        except:
                print("Program cannot be executed. Exiting...")

def execute_v2_command(controllers, cgroup_name, program):
        try:
                file = open(cgroupfs+cgroup_name+"/cgroup.procs", "a")
                file.write(str(os.getpid()))
                file.close()
                ret = subprocess.call(program, shell=True)
                if (ret != 0):
                        print(ret)
                        raise Exception("failed: ", program)
        except KeyboardInterrupt:
                print("Keyboard interrupt. Exiting...")
        except:
                print("Program cannot be executed. Exiting...")

def execute_command(cgroup_ver, controllers, cgroup_name, program, nolibcgroup):
        try:
                if (nolibcgroup == True):
                        raise Exception("No libcgroup. Use traditional interface") 
                command = "cgexec"
                for c in controllers:
                        command += " -g " + c + ":" + cgroup_name
                command += " " + ' '.join(map(str, program))
                ret = subprocess.call(command, shell=True)
                print(ret)
                if (ret != 0):
                        print(ret)
                        raise Exception("failed: ", command, ret) 
        except KeyboardInterrupt:
                print("Keyboard interrupt. Exiting...")
        except:
                if (cgroup_ver == 1):
                        execute_v1_command(controllers, cgroup_name, ' '.join(map(str, program)))
                else:
                        execute_v2_command(controllers, cgroup_name, ' '.join(map(str, program)))

def clean_v1_heir(controllers, cgroup_name):
        try:
                # remove dependent pids and then remove the directory
                for c in controllers:
                        open(cgroupfs+c+"/"+cgroup_name+"/tasks", "w").close()
                        os.rmdir(cgroupfs+c+"/"+cgroup_name)
        except:
                print("Could not clean up cgroup heirarchy. Exiting...")
                exit(1)

def clean_v2_heir(controllers, cgroup_name):
        try:
                # remove dependent pids and then remove the directory
                open(cgroupfs+cgroup_name+"/cgroup.procs", "w").close()
                os.rmdir(cgroupfs+cgroup_name)
        except:
                print("Could not clean up cgroup heirarchy. Exiting...")
                exit(1)

def clean_cgroup_heir(cgroup_ver, controllers, cgroup_name, nolibcgroup):
        try:
                if (nolibcgroup == True):
                        raise Exception("No libcgroup. Use traditional interface") 
                command = "cgdelete"
                for c in controllers:
                        command += " " + c + ":" + cgroup_name
                if os.system(command) != 0:
                         raise Exception("failed: ", command) 
        except:
                if (cgroup_ver == 1):
                        clean_v1_heir(controllers, cgroup_name)
                else:
                        clean_v2_heir(controllers, cgroup_name)

def get_all_cpus():
        return psutil.Process().cpu_affinity()

def parse_args():
        supported_controllers = ['cpu', 'cpuset']

        parser = argparse.ArgumentParser()
        parser.add_argument("--controllers", "-c",
                            help="Choose a controller cpus and/or cpuset",
                            type=str)
        parser.add_argument("--cgroup_name", "-n",
                            help="Choose a name for your cgroup. default: my_group",
                            default="my_group", type=str)
        parser.add_argument("--cpuset", help="cpuset limits. default: entire system", type=str)
        parser.add_argument("--cores", help="num of cpus needed, split between nodes default: all",
                            type=int)
        parser.add_argument("--nolibcgroup", help="Use traditional interfaces rather than libcgroup tools",
                            action="store_true")
        parser.add_argument("--period", help="cpu period us. default: 100000",
                            default=100000, type=int)
        parser.add_argument("--quota", help="cpu quota us. default: max",
                            default=-1, type=int)
        parser.add_argument("command", help="command to execute (in quotes)", nargs='*')

        args = parser.parse_args()

        if (not args.controllers):
                print("No controllers specifed. Use --help for help Exiting...")
                exit(1)
        args.controllers = args.controllers.split(',')
        if (not set(args.controllers).issubset(set(supported_controllers))):
                print("Unsupported controller(s):", args.controllers)
                exit(1)

        if ("cpuset" in args.controllers and (not args.cpuset) and (not args.cores)):
                args.cpuset = get_cpus.human_readable_cpuset(get_all_cpus())

        if (args.cores):
                cpu_list = get_cpus.get_cpus(args.cores)
                if (cpu_list != -1):
                        args.cpuset = get_cpus.human_readable_cpuset(cpu_list)

        return args

def dynamic_cpuset(cgroup_ver, args, cores_to_remove):

        cpu_list = get_cpus.get_cpus(args.cores)
        print(get_cpus.human_readable_cpuset(cpu_list))
        args.cpuset = get_cpus.human_readable_cpuset(cpu_list)

        threads_per_core = psutil.cpu_count() / psutil.cpu_count(logical=False)
        cpus_to_remove = int(cores_to_remove * threads_per_core)
        new_cpu_list = cpu_list

        while True:
                populate_cgroup_limits(cgroup_ver, args)

                sleep(180)
                if (len(new_cpu_list) == len(cpu_list)):
                        new_cpu_list = cpu_list[:-cpus_to_remove]
                elif (len(new_cpu_list) == len(cpu_list) - cpus_to_remove):
                        new_cpu_list = cpu_list[:]

                args.cpuset = get_cpus.human_readable_cpuset(new_cpu_list)


if __name__=="__main__":

        # Hardcoded for the test
        cores_to_remove = 5

        # Sanity root check
        if (os.geteuid() != 0):
                print("Need to run this script as root. Exiting...")
                exit(1)

        args = parse_args()

        # Determine if we are running Cgroup v1 or v2
        cgroupv1_iden = cgroupfs + "cpuset"
        cgroupv2_iden = cgroupfs + "cgroup.controllers"

        if (os.path.isdir(cgroupv1_iden)):
                cgroup_ver = 1
        elif (os.path.isfile(cgroupv2_iden)):
                cgroup_ver = 2
        else:
                print("Cgoup version unidentified. Exiting...")
                exit(1)

        print("Cgroup version:\t\t", cgroup_ver)
        print("Controllers invoked:\t" , args.controllers)
        if ("cpuset" in args.controllers):
                print("Cpuset limit:\t\t", args.cpuset)
        if ("cpu" in args.controllers):
                print("CPU period limit:\t", args.period)
                print("CPU quota limit:\t", args.quota)

        print("\nCreating cgroup heirarchy...")
        create_cgroup_heir(cgroup_ver, args.controllers, args.cgroup_name, args.nolibcgroup)
        print("Attaching limits...")
        populate_cgroup_limits(cgroup_ver, args)
        print("Executing program under cgroup...", args.command)
        print("\n")

        t1 = multiprocessing.Process(target=dynamic_cpuset, args=(cgroup_ver, args, cores_to_remove))
        t1.start()

        execute_command(cgroup_ver, args.controllers, args.cgroup_name, args.command, args.nolibcgroup)
        t1.terminate()
        clean_cgroup_heir(cgroup_ver, args.controllers, args.cgroup_name, args.nolibcgroup)
