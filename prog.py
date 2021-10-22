import os
os.environ["OMP_NUM_THREADS"] = "8" # export OMP_NUM_THREADS=4


 
import numpy as np
from numpy import pi

import math
import cmath
import scipy

import time

import sys

from qiskit_nature.problems.second_quantization.electronic.builders.fermionic_op_builder import build_ferm_op_from_ints
from qiskit_nature.converters.second_quantization import QubitConverter
from qiskit_nature.mappers.second_quantization import JordanWignerMapper

from qiskit_nature.operators.second_quantization import FermionicOp

from find_a import *
from second_q_op_vaz import *
from ps_mod import *
from anzatz import *
from routines import *

from quantum_mod import *

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
#Nelec = 2

name2l = {
  "s": 0,
  "p": 1,
  "d": 2
  }

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

def jl2k(j,l):
  return (-1)**int(l+j+0.5) * int(j + 0.5)

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

class rad_orb:
  def __init__(self,n,l,j):
    self.n = n
    self.j = j
    self.l = l

    self.k = (-1)**int(l+j+0.5) * int(j + 0.5)

    self.i = -1
  def __eq__(self, other):
    return self.k == other.k and self.n == other.n
  
  def __str__(self):
    return str(self.i) + " " + str(self.n) + " " + str(self.k)

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

class orb_cls:
  def __init__(self,n,k,m):
    self.n = n
    self.k = k
    self.m = m

    self.i = -1

    self.j = abs(k) - 0.5
    self.l = int( abs(k + 0.5) - 0.5 )

  def __eq__(self, other):
    return self.k == other.k and self.n == other.n and self.m == other.m

  def __str__(self):
    return str(self.i) + " " + str(self.n) + " " + str(self.k) + " " + str(self.m)

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

def find_orb(arr, indx, m):
  for i,x in enumerate(arr):
    if indx == x.i and m == x.m:
      return i
  return -1  

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -


# Read files --------------------------------------------------------
#fl_1b_int = open(sys.argv[1],"r")
#fl_2b_int = open(sys.argv[2],"r")
#norb_max = int(sys.argv[3])
fl_inp = open(sys.argv[1],"r")

for ln in fl_inp.readlines():
  if ln == "\n":
    continue

  key, val = ln.strip().replace(" ","").split("=")
  if key == "OBI":
    fl_1b_int = open(val,"r")

  if key == "TBI":
    fl_2b_int = open(val,"r")

  if key == "Nelec":
    Nelec = int(val)

  if key == "norb":
    norb_max = int(val)

  if key == "anzatz_tp":
    anzatz_tp = int(val)

  if key == "Nlayers":
    Nlayers = int(val)

  if key == "rot":
    rot = [int(x) for x in val.replace("[","").replace("]","").split(",")]

  if key == "Q_on":
    Q_on = (val == "True")

  if key == "noise_off":
    noise_off = (val == "True")

  if key == "Nrep":
    Nrep = int(val)

#exit()


# reading one-electron orbitals - - - - - - - - - - - - - - - - - - -
read_states = False
rad_orb_arr = []
for ln in fl_1b_int.readlines():
  if ln == "\n":
    continue

  arr = ln.split()

  if arr[0] == "Ni":
    read_states = True
    continue
  
  if arr[0] == "n1":
    break

  if read_states:
    sz = len(arr[1])
    n = int( arr[1][:sz-1] )
    l = name2l[ arr[1][sz-1] ]
    j = 0.5*float( arr[3].split("/")[0] )
    indx = int(arr[0])
    
    rad_orb_arr.append( rad_orb(n,l,j) )
    rad_orb_arr[-1].i = indx
# End reading one-electron orbitals - - - - - - - - - - - - - - - - -


# creating spin-orbitals - - - - - - - - - - - - - - - - - - - - - - 
orb_arr = []

norb = 0
delete_from = -1
for i,x in enumerate(rad_orb_arr):
  if norb + 2*x.j + 1 > norb_max:
    delete_from = i
    break
  norb += int(2*x.j + 1)


sz = len(rad_orb_arr) - delete_from
for i in range(sz):
  if delete_from == -1:
    continue
  rad_orb_arr.pop(delete_from)
  

#print("norb = ", norb)
# find maximal j
jmax = max([x.j for x in rad_orb_arr])

for s in range(-1,2,2):
  for m in range( 1, int(2*jmax+1)+1, 2 ):
    for x in rad_orb_arr:
      if 0.5*m > x.j:
        continue
      orb_arr.append( orb_cls(x.n, x.k, 0.5*m*s) )
      orb_arr[-1].i = x.i

print("\nFollowing orbitals are used")
for x in orb_arr:
  print(x)


one_b_int = np.zeros([norb,norb])
two_b_int = np.zeros([norb,norb,norb,norb])


fl_1b_int.seek(0)
# end creating spin-orbitals - - - - - - - - - - - - - - - - - - - - 


# Read one-body integrals - - - - - - - - - - - - - - - - - - - - - -
read_int = False
for ln in fl_1b_int.readlines():
  if ln == "\n":
    continue

  arr = ln.split()
  if arr[0] == "n1":
    read_int = True
    continue

  if read_int:
    i = int(arr[0])
    j = int(arr[1])
    h_ij = float( arr[2] )
    
    for iorb,x in enumerate(orb_arr):
      for jorb,y in enumerate(orb_arr):
        if x.m == y.m and i == x.i and j == y.i:
          one_b_int[iorb,jorb] = h_ij
          one_b_int[jorb,iorb] = h_ij
# End reading one-body integrals - - - - - - - - - - - - - - - - - - 

# Read one-body integrals - - - - - - - - - - - - - - - - - - - - - -
read_int = False
for ln in fl_2b_int.readlines():
  if ln == "\n":
    continue

  arr = ln.split()

  if arr[0] == "n1":
    read_int = True
    continue

  if read_int:
    i = np.zeros((4),dtype=int)
    for ii in range(4):
      i[ii] = int( arr[ii] )

    m = np.zeros((4),dtype=float)
    for ii in range(4):
      m[ii] = 0.5*float( arr[4+ii] )
      
    u_coul_dir = float( arr[8] )
    u_coul_ex = float( arr[9] )
    u_br_dir = float( arr[10] )
    u_br_ex = float( arr[11] )

    p = find_orb(orb_arr, i[0], m[0])
    if p == -1:
      continue
    q = find_orb(orb_arr, i[1], m[1])
    if q == -1:
      continue
    r = find_orb(orb_arr, i[2], m[2])
    if r == -1:
      continue    
    s = find_orb(orb_arr, i[3], m[3])
    if s == -1:
      continue

    # direct
    two_b_int[p,q,r,s] = u_coul_dir + u_br_dir
    two_b_int[q,p,s,r] = u_coul_dir + u_br_dir

    two_b_int[s,r,q,p] = u_coul_dir + u_br_dir
    two_b_int[r,s,p,q] = u_coul_dir + u_br_dir

    # exchange
    two_b_int[p,q,s,r] = u_coul_ex + u_br_ex
    two_b_int[q,p,r,s] = u_coul_ex + u_br_ex

    two_b_int[r,s,q,p] = u_coul_ex + u_br_ex
    two_b_int[s,r,p,q] = u_coul_ex + u_br_ex

# ===================================================================


# Construct the Hamiltonian as a fermion operator -------------------
qubit_converter = QubitConverter(mapper=JordanWignerMapper())

H_op = 0*FermionicOp("I"*norb).reduce()


# This term will add some energy to the states with wrong particle number
if anzatz_tp == 0:
  N_part_op = build_ferm_op_from_ints(one_body_integrals=np.identity(norb))
  H_op += 10*(N_part_op - Nelec*FermionicOp("I"*norb))**2


#Add one-body integrals
for p in range(norb):
  for q in range(norb):
    if one_b_int[p,q] == 0:
      continue
    
    coef, lbl = second_q_op_pq(p, q, norb)
    H_op += coef * FermionicOp(lbl) * one_b_int[p,q]


#Add two-body integrals
for p in range(norb):
  for q in range(norb):
    if p == q:
      continue
    for r in range(norb):
      for s in range(norb):
        if r == s:
          continue

        if two_b_int[p,q,r,s] != 0.0:
          coef, lbl = second_q_op_pqrs(p, q, s, r, norb)

          H_op += 0.5 * coef * FermionicOp(lbl) * two_b_int[p,q,r,s]

H_op = H_op.reduce()
#print("\n",H_op)
#exit()


# Rewrite Hamiltonian as a sum of Pauli strings ---------------------
H_q = qubit_converter.convert(H_op)

Nq = H_q.num_qubits
print( "Nq = ", Nq, flush=True )


# Number of particles -----------------------------------------------
N_part_op = build_ferm_op_from_ints(one_body_integrals=np.identity(Nq))
N_part_q = qubit_converter.convert(N_part_op)
N_part_mtrx = N_part_q.to_matrix().real
# -------------------------------------------------------------------


# Jz matrix ---------------------------------------------------------
tmp = np.identity(Nq)
for i,orb in enumerate(orb_arr):
  tmp[i,i] = orb.m

Jz_op = build_ferm_op_from_ints(one_body_integrals=tmp)
Jz_q = qubit_converter.convert(Jz_op)
Jz_mtrx = Jz_q.to_matrix().real
#exit()
# -------------------------------------------------------------------


# Total Hamiltonian matrix ------------------------------------------
H_mtrx = H_q.to_matrix().real

# Find eigenvalues and eigenvectors of the Hamiltonian
energy, wf = np.linalg.eigh(H_mtrx)


# Diagonalize Jz matrix ---------------------------------------------
indx_arr = [0]
for i in range(1,2**Nq):
  diff = energy[i]-energy[i-1]

  if diff < 5.e-14:
    indx_arr.append(i)
    continue

  # Cluster of the states with the same energies, 
  # number of particles, and parities is created
  # Calculate Jz matrix for this cluster
  sz = len(indx_arr)
  Jz_mtrx_new = np.zeros((sz,sz))
  for r in range(sz):
    for c in range(r, sz):
      jz = np.conj(wf[:,indx_arr[r]].T).dot( 
        Jz_mtrx.dot( wf[:,indx_arr[c]]) 
        ).item(0)

      Jz_mtrx_new[r,c] = jz
      Jz_mtrx_new[c,r] = jz


  val, vec = np.linalg.eigh(Jz_mtrx_new)

  wf[:,indx_arr] = np.matmul(wf[:,indx_arr],vec)

  # Preparation for a new cluster
  indx_arr = [i]
#exit()
# -------------------------------------------------------------------


# Find the energy of the ground and first excited states
# for each possible number of electrons
ne_arr = range(norb+1)
indx_g = [-1]*(norb+1)
indx_e = [-1]*(norb+1)

for i in range(2**Nq):
  npart = np.conj(wf[:,i].T).dot( N_part_mtrx.dot( wf[:,i]) ).item(0)  
  jz = np.conj(wf[:,i].T).dot( Jz_mtrx.dot( wf[:,i]) ).item(0)

  #if int( round(npart)) == Nelec:
    #print( energy[i], jz )

  for ii, x in enumerate(ne_arr):
    if int(round(npart)) == x:
      if indx_g[ii] == -1:
        indx_g[ii] = i
        break
      # condition abs(...) > 1.e-13 is needed to get rid of degenerate states
      if indx_e[ii] == -1 and abs(energy[i] - energy[indx_g[ii]]) > 1.e-13:
        indx_e[ii] = i
        #break


    
print("\n","Ne", 
      f'{"Eg": >8}', 
      f'{"Ee": >8}', 
      f'{"Jz": >4}', 
      f'{"Ndet": >5}', 
      f'{"Nconf": >7}')
for i, ne in enumerate(ne_arr):
  #if ne != Nelec:
    #continue
  
  indx = np.argsort( abs(wf[:,indx_g[i]]), axis=0 )
  jz_g = get_jz( orb_arr, bin( indx[-1] )[2:].zfill(Nq) )
  parity_g = get_parity( orb_arr, bin( indx[-1] )[2:].zfill(Nq) )

  Sl_det = []
  conf_arr = []
  for ii in range(2**Nq):
    bn = bin(ii)[2:].zfill(Nq)
    jz = get_jz( orb_arr, bn )
    parity = get_parity( orb_arr, bn )

    if bn.count("1") == ne and jz == jz_g and parity == parity_g:
      Sl_det.append(bn)
      #print(bn)

      conf = bin_to_conf( orb_arr, bn )
      if not (conf in conf_arr):
        conf_arr.append(conf)

  NSl_det = len(Sl_det)

  if indx_e[i] != -1:
    print(f'{ne: >3}', 
          f'{energy[indx_g[i]]: .5f}', 
          f'{energy[indx_e[i]]: .5f}', 
          f'{jz_g: 4.1f}', 
          f'{NSl_det: > 5}', 
          f'{len(conf_arr): >7}')
  else:
    print(f'{ne: >3}', 
          f'{energy[indx_g[i]]: .5f}', 
          " "*8,
          f'{jz_g: 4.1f}', 
          f'{NSl_det: > 5}', 
          f'{len(conf_arr): >7}')

  # All possible Slater Determinants
  #for det in Sl_det:
    #print(det)
#exit()
# -------------------------------------------------------------------




# Imaginary time propagation ========================================
#Q_on = True
#noise_off = True
create_noise_model(Nq, Nrep)


# Not all Pauli matrices have to be measured - - - - - - - - - - - - 
if Q_on:
  ps_meas, indx_ps2meas = extract_ps_for_measurement(H_q)
  print("Hamiltonian consists of",len(indx_ps2meas),"PS", flush=True )
  print("It is sufficient to measure", len(ps_meas), "of them", flush=True)
#exit()
# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -


dtau = 0.5
# In principle the value of dtau and the difference in energy between 
# ground and excited states defines the number of necessary steps
# for propagation in imaginary time


# Preparation -------------------------------------------------------
#anzatz_tp = 0
#Nlayers = 1
#rot = []

Uent = None
Uent_circ = None

if anzatz_tp == 0:
  rot = [2]
  # in rot can be any number of rotations
  # values can be only 1,2, or 3 related to Rx, Ry, and Rz, respectively
  #
  # --- rot[1](ang_0) --- rot[2](ang_4) ---.-------
  #                                        |
  # --- rot[1](ang_1) --- rot[2](ang_5) ---x-.-----
  #                                          |
  # --- rot[1](ang_2) --- rot[2](ang_6) -----x-.---
  #                                            |
  # --- rot[1](ang_3) --- rot[2](ang_7) -------x---
  #
  # + final layer of rotations
  Nparam = (Nlayers + 1) * Nq * len(rot)
  Uent = entangling_mtrx(Nq)
  if Q_on:
    Uent_circ = entangling_circ(Nq)
    print(Uent_circ)


if anzatz_tp == 1:
  # ---.-------
  #    |
  #   [R](ang_0)
  #    |
  # ---.------.---
  #           |
  #          [R](ang_2)
  #           |
  # ---.------.---
  #    |
  #   [R](ang_1)
  #    |
  # ---.-------
  Nparam = Nlayers * (Nq - 1)

if anzatz_tp == 2:
  Nparam = 4


rot_ang_c = math.pi*(2*np.random.rand(Nparam)-1)
rot_ang_q = rot_ang_c.copy()
print("Total number of parameters in anzatz = ", Nparam, flush=True)



# Calculate derivative matrices for classical calculations
dU = deriv_mtrx(anzatz_tp, rot, Nq)


# Exact ground-state wave function for given number of electrons
psi_exact = wf[:,indx_g[Nelec]].copy()
np.save("psi_exact", psi_exact)


indx = np.argsort( abs(psi_exact), axis=0 )
print("\n","Exact wave function (dominant contributions)")
for i in range(2**Nq):
  ii = indx[2**Nq-1-i]
  bn_ii = bin(ii)[2:].zfill(Nq)
  x = psi_exact[ ii ]

  if abs(x)**2 > 1.e-15:
    print( f'{i: >2}', 
          bn_ii, 
          x,
          f'{abs(x)**2: .5f}', 
          bin_to_conf( orb_arr, bn_ii ), flush=True)


# Dominant contribution comes from the Slater determinant
# with the binary representation 
psi_i_bn = bin( 
  int( np.argsort( abs(psi_exact), axis=0 )[-1] ) 
  )[2:].zfill(Nq)

if anzatz_tp == 2:
  psi_i_bn = "00110010"
print("\n","Initial guess = ", psi_i_bn, flush=True)


#exit()
# Convert to the Pauli string of X and I gates 
# for preparation as a quantum circuit
psi_i_ps = [ psi_i_bn[i] for i in range(Nq)]

if Q_on:
  psi_i_circ = ps_2_circ(psi_i_ps)
  print(psi_i_circ)

  

# For evaluation by classical algorithms we need a vector
psi_i_vec = ps_2_vec(psi_i_ps, Nq)
np.save("psi_in", psi_i_vec)
#exit()


# Check anzatz - - - - - - - - - - - - - - - - - - - - - - - - - - - 
def fun(vctr):
  psi_f_vec = apply_anzatz(anzatz_tp, rot, Nlayers, vctr, Nq,
                           psi_i_vec, Uent)

  diff = np.linalg.norm(psi_f_vec - psi_exact)**2.0
  #E = (psi_f_vec.conj().T).dot( H_mtrx.dot(psi_f_vec) ).item().real
  return diff

def dfun(vctr):
  res = np.zeros((Nparam),dtype=float)

# All layers are calculated and stored since they will be used 
# Nparam = len(vctr) times for the evaluation of the derivative
  U = anzatz_matrices(anzatz_tp, rot, Nlayers, vctr, Nq)

  for a in range(Nparam):
    dpsi_f_vec = apply_danzatz(anzatz_tp, rot, Nlayers, vctr, Nq, 
                               U, dU, a, psi_i_vec, Uent)

    res[a] = -2 * (dpsi_f_vec.conj().T).dot( psi_exact ).item(0).real



  return res

rot_ang_bst = scipy.optimize.minimize(fun, 
                                      rot_ang_c, 
                                      method='Newton-CG', 
                                      jac=dfun, 
                                      tol=1.e-12).x


#print("Best rotation angles \n", 
      #np.array([x - 2*pi*math.floor(x/(2*pi)) for x in rot_ang_bst]) )
#print("Best rotation angles \n", rot_ang_bst/pi, flush=True )

psi_f_vec = apply_anzatz(anzatz_tp, rot, Nlayers, rot_ang_bst, Nq,
                         psi_i_vec, Uent)

diff = np.linalg.norm(psi_f_vec - psi_exact)**2.0
print( "Diff with exact wf = ", diff, flush=True )


print( "\n", " "*Nq, f'{"exact": >7}', f'{"approx": >8}', flush=True )
for i in range(2**Nq):
  if abs(psi_f_vec[i])**2 > 1.e-5 or abs(psi_exact[i])**2 > 1.e-5:
    print( bin(i)[2:].zfill(Nq), 
          f'{abs(psi_exact[i])**2: .5f}', 
          f'{abs(psi_f_vec[i])**2: .5f}', flush=True
          )

E = (psi_f_vec.conj().T).dot( H_mtrx.dot(psi_f_vec) ).item().real
print("\n","For these angles one obtains E_g = ", E, 
      "\n","diff with exact = ", f'{E - energy[indx_g[Nelec]]: .1e}',
      flush=True)
#exit()
# Anzatz checked ----------------------------------------------------




# VQE ===============================================================
VQE_on = True
if VQE_on:
  E_q = measure_Ham(anzatz_tp, psi_i_circ, Uent_circ,
                    Nlayers, rot, rot_ang_bst, 
                    ps_meas, indx_ps2meas, H_q, 
                    noise_off=noise_off)
  print("E_VQE = ", E_q)
# ===================================================================




# Propagation in accordance to McArdle ==============================
U = anzatz_matrices(anzatz_tp, rot, Nlayers, rot_ang_c, Nq)
for it in range(100000):
  A_mtrx_c = np.zeros((Nparam,Nparam),dtype=float)
  C_vec_c = np.zeros((Nparam),dtype=float)

  if Q_on:
    A_mtrx_q = np.zeros((Nparam,Nparam),dtype=float)
    C_vec_q = np.zeros((Nparam),dtype=float)

  psi_c = apply_anzatz(anzatz_tp, rot, Nlayers, rot_ang_c, Nq,
                       psi_i_vec, Uent)

# Calculate C -------------------------------------------------------
  for a in range(Nparam):
    dpsi_c_a = apply_danzatz(anzatz_tp, rot, Nlayers, rot_ang_c, Nq, 
                               U, dU, a, psi_i_vec, Uent)

    C_vec_c[a] = -2 * (dpsi_c_a.conj().T).dot( H_mtrx.dot(psi_c) ).item(0).real


    if Q_on:
      C_vec_q[a] = -clc_c_vec(anzatz_tp, psi_i_circ, Uent_circ, 
                             Nlayers, rot, rot_ang_q, a,
                             ps_meas, indx_ps2meas, H_q,
                             noise_off=noise_off)
      #print("C_vec_q[a] = ", C_vec_q[a])

      
# Calculated A matrix -----------------------------------------------
    for b in range(a, Nparam):
      dpsi_c_b = apply_danzatz(anzatz_tp, rot, Nlayers, rot_ang_c, Nq, 
                                U, dU, b, psi_i_vec, Uent)

      A_mtrx_c[a,b] = 2*(dpsi_c_a.conj().T).dot( dpsi_c_b ).item(0).real
      A_mtrx_c[b,a] = A_mtrx_c[a,b]

      if Q_on:
        A_mtrx_q[a,b] = clc_a_mtrx(anzatz_tp, psi_i_circ, Uent_circ,
                                   Nlayers, rot, rot_ang_q, a, b,
                                   noise_off=noise_off)
        A_mtrx_q[b,a] = A_mtrx_q[a,b]


# Calculate new values of angles ------------------------------------
  dtheta_c = solve_Ax_b(A_mtrx_c, C_vec_c)
  rot_ang_c += dtau * dtheta_c
  


# Average value of Hamiltonian and wf measurements ------------------
  U = anzatz_matrices(anzatz_tp, rot, Nlayers, rot_ang_c, Nq)
  psi_c = apply_anzatz(anzatz_tp, rot, Nlayers, rot_ang_c, Nq,
                       psi_i_vec, Uent)

  E = (psi_c.conj().T).dot( H_mtrx.dot(psi_c) ).item().real


# It will be nice to reduce the step (dtau), when 
# the local minima is found
  if it%100 == 0:
    print("<E> = ", f'{E: .5f}', 
          "|psi - psi_exct| = ", 
          f'{ np.linalg.norm(psi_c - psi_exact)**2.0: .1e}',
          np.amax(abs(dtheta_c)), flush=True)
  if np.amax(abs(dtheta_c)) < 1.e-3:
    break


print("Best rotation angles \n", rot_ang_bst/pi, flush=True )
print("Angles from imaginary time\n", rot_ang_c/pi%2, flush=True )


# On output we have
print( "\n", " "*Nq, f'{"exact": >7}', f'{"approx": >8}', flush=True )
for i in range(2**Nq):
  if abs(psi_c[i])**2 > 1.e-5 or abs(psi_exact[i])**2 > 1.e-5:
    print( bin(i)[2:].zfill(Nq), 
          f'{abs(psi_exact[i])**2: .5f}', 
          f'{abs(psi_c[i])**2: .5f}', 
          flush=True)
