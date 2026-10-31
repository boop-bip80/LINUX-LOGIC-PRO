#!/usr/bin/env python3
"""Independent Git metadata boundary checks; disposable fixtures only."""
import importlib.util
import json
from pathlib import Path
import sys

root=Path(sys.argv[1]).resolve()
spec=importlib.util.spec_from_file_location("meta_fixture",root/"tests/compat/logic-pro/submodules/test_lock.py")
m=importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

def trial(name, mutate):
    f=m.RealRecursiveClone(); f.setUp()
    try:
        m.git(f.clone,"config","user.name","Adversarial review")
        m.git(f.clone,"config","user.email","review@example.invalid")
        details=mutate(f)
        try:
            verdict=f.check()["result"]
        except Exception as e:
            verdict="REJECTED: "+type(e).__name__+": "+str(e)
        return {"case":name,"verifier":verdict,**details}
    except Exception as e:
        return {"case":name,"fixture_operation_rejected":type(e).__name__+": "+str(e)}
    finally:
        f.doCleanups()

def update_none(f):
    m.git(f.clone,"config","--file",".gitmodules","submodule.sub.update","none")
    m.commit(f.clone,"add update=none")
    fresh=Path(f.temp.name)/"fresh-recursive-clone"
    m.git(None,"clone","-q","--recurse-submodules",f.clone.as_uri(),str(fresh))
    status=m.git(fresh,"submodule","status","--recursive")
    return {"fresh_clone_status":status,"fresh_child_initialized":(fresh/"sub"/".git").exists()}

def modules_symlink(f):
    p=f.clone/".gitmodules"; content=p.read_text()
    oid=m.git(f.clone,"rev-parse","HEAD:.gitmodules")
    p.unlink(); p.symlink_to(content)
    m.git(f.clone,"update-index","--cacheinfo","120000",oid,".gitmodules")
    m.git(f.clone,"commit","-q","-m","symlink modules")
    return {"gitmodules_mode":m.git(f.clone,"ls-tree","HEAD",".gitmodules")}

print(json.dumps({"commit":m.git(root,"rev-parse","HEAD"),"cases":[trial("committed_update_none",update_none),trial("committed_gitmodules_symlink",modules_symlink)]},indent=2))
