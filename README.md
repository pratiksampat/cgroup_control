# Cgroup Control

A simple hacky script that allows you to create, manage and execute within cpu and cpuset cgroups

## Why this script?
Q: Why use this script rather than use a tools like libcgroup or even container creation tools like docker?

A: Tools like docker are heavy and not enough control each aspect via cgroups.

libcgroups are good, however each tool like cgcreate, cgmodify and cgexec are seperate entities and this script unfies their use. Also these tools are not always available, hence fallbacks are written to plug in directly into cgroup regardless of v1 or v2.

## Running this program

cgroup_control.py is the entry point script which uses get_cpus.py as module. The latter can run independently as well, more and that later.

### Running cgroup_control.py

Instructions to run

```bash
Instructions to run:
# ./cgroup_control.py \
        --controllers <controlers comma seperated>\
        --cpuset="<cpuset>"\
        --period=<integer> --quota=<integer> \
        "<command in quotes>"
```

Sample way of running

```bash
# ./cgroup_control.py \
        --controllers cpuset,cpu\
        --cpuset="0-3"\
        --period=100000 --quota=30000 \
        "cat /dev/random > /dev/null"
```

This will create two controllers cpuset and cpu.
Cpuset restrited cpus 0-3. Cpu controller restricted with period=100000us and quota=30000. The cgroup will be called my_group as that is the default

All the options are described here as follows:

```
1. --controllers or -c => Comma seperated. Currently supports cpu and cpuset controllers
2. --cgroup_name or -n => Name of the cgroup folder. Default: my_group
3. --cpuset => List of cpus that you wish to bind to (Needs: cpuset controller). Default: all cpus
4. --cores => Specify number of cores you want and a list will be generated equally divided between all the numa nodes.
5. --nolibcgroup => Use this option to disable the use of libcgroup. Useful for malfunctioning packages.
6. --period => CPU period in us (Needs: cpu controller). Default: 100000
7. --quota => CPU quota in us (Needs: cpu controller). Default: -1 (max quota) 
```

> Use `--nolibcgroup` to disable the use of libcgroup. This will fallback to the old ways to using cgroupfs interface directly. This option exists because sometime some cg* packages fail while giving a return 0 to the program.

### Difference between `--cpuset` vs `--cores`
cpuset is used to specify the exact list of cpus you wish to bind to.

cores is used to specify a number of cores you which to attach. cpus will be then calcucated with cores * num_thread. This option also equally divides the number of cores between various numa nodes as well.

Note: When both cpuset and cores are used. Cores takes a higher precedence and that is used instead.

### Running get_cpus.py

The option to extract cores is abstracted out into a module such that if only the number of cores are needed then just get_cpus.py can also be run.

This can be run as a module as follows

```py
from get_cpus import get_cpus

print(get_cpus(<num_of_cores>))
```

Just running get_cpus.py

```bash
$ python3 get_cpus.py --cores <num_of_cores>
```
This will return a string of cpus that can directly be plugged into cpuset.

> As this script is currently designed for Power systems hence the threads for each core logic is consequtive however that is not true for other platforms such as x86.
In future, update this script to identify thread sibilings via sysfs.