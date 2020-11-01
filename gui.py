from tkinter import *
from tkinter import filedialog
from tkinter import messagebox
from tkinter import font


from gurobipy import *

import time
import ntpath

from file import *


fix_dependencies()

root = Tk()
root.title("Idol")
root.iconbitmap('favicon.ico')
root.geometry("500x500")

root.ystar = {}
WRKDIR = "wrkdir"

lbl_text = StringVar()
lbl_text.set("No file has been loaded")

gui_font = font.Font(family='Helvetica', size=12)


def get_obj_num(model):
    # get # of objectives
    NumOfObj = model.getAttr(GRB.Attr.NumObj)
    print('Number of objectives: ', NumOfObj)

    objs_lbl = Label(root, text="Number of Objectives: " + str(NumOfObj))
    objs_lbl.pack()

    return NumOfObj


def create_vars(model, mo, NumOfObj):
    varDict = {}

    # add single objective variable
    sv = mo.addVar(vtype=GRB.CONTINUOUS, name='s')
    varDict['s'] = sv

    # create variables for multiple objectives
    for i in range(NumOfObj):
        ov = mo.addVar(vtype=GRB.CONTINUOUS, name='f' + str(i + 1))
        varDict['f' + str(i + 1)] = ov

    # copy variables from multiobjective model
    for v in model.getVars():
        mv = mo.addVar(lb=v.lb, ub=v.ub, obj=v.obj, vtype=v.vtype, name=v.varname)
        varDict[v.varname] = mv
    mo.update()

    return varDict


def constr_from_obj(model, mo, NumOfObj, varDict):

    # constraints from objectives
    for i in range(NumOfObj):
        obj = model.getObjective(i)
        newexpr = LinExpr()
        ov = varDict['f' + str(i + 1)]
        for j in range(obj.size()):
            v = obj.getVar(j)
            coeff = obj.getCoeff(j)

            newv = varDict[v.varname]
            newexpr.add(newv, coeff)

        newexpr.add(ov, -1)
        mo.addConstr(newexpr == 0, name='f' + str(i + 1))


def constr_chebyshev(mo, NumOfObj, varDict, ystar, rho, lmbd):
    sum_term = 0
    weight_term = []

    for i in range(NumOfObj):
        sum_term += rho * (ystar[i] - varDict['f' + str(i + 1)])

    for i in range(NumOfObj):
        weight_term.append(lmbd[i] * (ystar[i] - varDict['f' + str(i + 1)]))

    for i in range(NumOfObj):
        mo.addConstr(varDict['s'] - weight_term[i] - sum_term >= 0, name='s' + str(i + 1))


def constr_copy(model, mo, varDict):
    # copy constraints
    for c in model.getConstrs():
        expr = model.getRow(c)

        newexpr = LinExpr()
        for j in range(expr.size()):
            v = expr.getVar(j)
            coeff = expr.getCoeff(j)
            newv = varDict[v.varname]
            newexpr.add(newv, coeff)
        mo.addConstr(newexpr, c.Sense, c.RHS, name=c.ConstrName)
    mo.update()


def save_model(model, name, type):
    make_dir()
    timestr = time.strftime("%Y%m%d-%H%M%S")

    if type == 'input':
        file_path = WRKDIR + "\\" + ntpath.basename(name)
    elif type == 'ch':
        file_path = WRKDIR + "\\Chebyshev_" + ntpath.basename(name)


    model.write(file_path)
    return file_path


def save_file(filename):
    try:
        model = read(filename)
        root.model_path = save_model(model, filename, 'input')

    except GurobiError as e:
        print('Error code ' + str(e.errno) + ': ' + str(e))


def load_file():

    try:
        root.filename = filedialog.askopenfilename(initialdir='',
                                                   title="Load a File",
                                                   filetypes=(("lp files", "*.lp"), ("all files", "*.*")))
        save_file(root.filename)
        print('File load is done!')

    except Exception as e:
        messagebox.showwarning("Warning", "File is not loaded")
        print('Error: ' + str(e))
        return

    try:
        lbl_text.set("File is loaded: " + root.model_path)
    except Exception as e:
        messagebox.showwarning("Error", "File is not loaded")
        print('Error: ' + str(e))
        return


def gen_reference():
    try:
        model = read(root.model_path)

        NumOfObj = model.getAttr(GRB.Attr.NumObj)
        modelDict = {}
        varDict = {}

        for i in range(NumOfObj):
            modelDict["mo_"+str(i)] = Model("NewModel_"+str(i))

            # copy variables from multiobjective model
            for v in model.getVars():
                mv = modelDict["mo_"+str(i)].addVar(lb=v.lb, ub=v.ub, obj=v.obj, vtype=v.vtype, name=v.varname)
                varDict[v.varname] = mv

            # copy constraints
            constr_copy(model, modelDict["mo_"+str(i)], varDict)

            # objectives
            obj = model.getObjective(i)
            objexpr = LinExpr()

            for j in range(obj.size()):
                v = obj.getVar(j)
                coeff = obj.getCoeff(j)

                newv = varDict[v.varname]
                objexpr.add(newv, coeff)

            modelDict["mo_"+str(i)].setObjective(objexpr, GRB.MAXIMIZE)
            modelDict["mo_"+str(i)].Params.MIPGap = 0.1
            modelDict["mo_"+str(i)].optimize()
            print('Obj {}: {} '.format(i+1, modelDict["mo_" + str(i)].objVal))
            root.ystar["mo_" + str(i)] = modelDict["mo_" + str(i)].objVal
            modelDict["mo_"+str(i)].write(WRKDIR+"/model_"+str(i + 1)+".lp")

            lbl_text.set("reference point generated")
            print("Reference point calculation is done!")

    except Exception as e:
        messagebox.showerror("Error", "File is not loaded")
        print('Error: ' + str(e))
        return


def load_weights():
    try:
        root.weights_file = filedialog.askopenfilename(initialdir='',
                                                   title="Load Weights",
                                                   filetypes=(("txt files", "*.txt"), ("all files", "*.*")))
        root.weights = read_txt(root.weights_file)
        print("Weights load is done!")

    except Exception as e:
        messagebox.showwarning("Warning", "Weights are not loaded")
        print('Error: ' + str(e))
        return

    try:
        lbl = ''
        for i in root.weights:
            lbl = lbl + str(i) + '  '

        lbl_text.set("Weights are loaded: " + lbl)
    except Exception as e:
        messagebox.showwarning("Error", "Weights are not loaded")
        print('Error: ' + str(e))
        return


def gen_chebyshev():
    try:
        model = read(root.model_path)

        mo = Model("NewModel")

        rho = 0.001
        # lmbd = [0.22, 0.222, 0.558]
        if bool(root.weights):
            lmbd = root.weights
        else:
            messagebox.showerror("Error", "Weights are not loaded")
            return

        NumOfObj = model.getAttr(GRB.Attr.NumObj)
        ystar = []

        varDict = create_vars(model, mo, NumOfObj)

        if bool(root.ystar):
            for k, v in root.ystar.items():
                ystar.append(v)
            print("MIPGap ystar")
        else:
            messagebox.showerror("Error", "Reference point is not calculated")
            return

        [print("MIPGap "+str(y)) for y in ystar]

        constr_chebyshev(mo, NumOfObj, varDict, ystar, rho, lmbd)

        constr_from_obj(model, mo, NumOfObj, varDict)

        constr_copy(model, mo, varDict)

        # set objective
        mo.setObjective(varDict['s'], GRB.MINIMIZE)

        root.ch_path = save_model(mo, root.model_path, 'ch')

        lbl_text.set("Chebyshev scalarization file: " + root.ch_path)
        print("Chebyshev scalarization is done!")

    except Exception as e:
        messagebox.showerror("Error", "File is not loaded")
        print('Error: ' + str(e))
        return


def optimize():
    try:
        ch_model = read(root.ch_path)
    except Exception as e:
        messagebox.showerror("Error", "Chebyshev scalarization is not generated")
        print('Error: ' + str(e))
        return

    ch_model.optimize()
    ch_model.write(WRKDIR+"/ch.sol")
    lbl_text.set("solution obtained: " + WRKDIR + "/ch.sol")
    print("Optimization is done!")


load_btn = Button(root, text="Load File", padx=400, pady=25, command=load_file)
load_btn.pack()
load_btn['font'] = gui_font

ref_btn = Button(root, text="Generate Reference Point", padx=400, pady=25, command=gen_reference)
ref_btn.pack()
ref_btn['font'] = gui_font

wght_btn = Button(root, text="Load Weights", padx=400, pady=25, command=load_weights)
wght_btn.pack()
wght_btn['font'] = gui_font

gen_btn = Button(root, text="Generate Chebyshev Scalarization", padx=400, pady=25, command=gen_chebyshev)
gen_btn.pack()
gen_btn['font'] = gui_font

opt_btn = Button(root, text="Optimize Chebyshev Scalarization", padx=400, pady=25, command=optimize)
opt_btn.pack()
opt_btn['font'] = gui_font

file_lbl = Message(root, textvariable=lbl_text, width=420)
file_lbl.pack()
file_lbl['font'] = gui_font

root.mainloop()
