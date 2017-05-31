import yaml
import os

CFG_FILE = "conf.yaml"

def load_conf(cfg_file=CFG_FILE):
    with open(cfg_file) as fh:
        cfgstr = yaml.dump(yaml.safe_load(fh))

    # replace env vars
    for k, v in os.environ.items():
        cfgstr = cfgstr.replace("${}".format(k), v)
    return dict(yaml.safe_load(cfgstr))


if __name__ == "__main__":
    print(load_conf())
    

