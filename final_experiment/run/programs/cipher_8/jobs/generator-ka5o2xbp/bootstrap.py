import resource, runpy
resource.setrlimit(resource.RLIMIT_CPU, (120, 120))
resource.setrlimit(resource.RLIMIT_FSIZE, (4194304, 4194304))
resource.setrlimit(resource.RLIMIT_NOFILE, (64, 64))
runpy.run_path('/Users/cmy/Desktop/aaai_rebuttal/runs/gpt52_final_20261028/programs/cipher_8/jobs/generator-ka5o2xbp/generator.py', run_name='__main__')
