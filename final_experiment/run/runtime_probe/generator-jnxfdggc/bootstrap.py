import resource, runpy
resource.setrlimit(resource.RLIMIT_CPU, (60, 60))
resource.setrlimit(resource.RLIMIT_FSIZE, (4194304, 4194304))
resource.setrlimit(resource.RLIMIT_NOFILE, (64, 64))
runpy.run_path('/Users/cmy/Desktop/aaai_rebuttal/runs/gpt52_final_20261028/runtime_probe/generator-jnxfdggc/generator.py', run_name='__main__')
