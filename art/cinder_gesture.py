"""Bake two relative hand gestures into the ash-painted GLB, before skinning."""
import numpy as np


def add_gestures(doc, data, primitive, position, normals, indices):
    # Define proximal hinges and signed lateral displacement along each digit.
    # Positions are metres in the 3.7 m tall character's neutral pose.
    digits = [
        (.945, 2.415, .57, .086, .20, -.14),
        (1.177, 2.435, .67, .111, .38, -.08),
        (1.355, 2.410, .64, .090, .39, .07),
        (1.459, 2.448, .63, .076, .28, .17),
    ]
    def write(values):
        arr = np.asarray(values, dtype="<f4")
        data.extend(bytes((-len(data)) % 4))
        view = len(doc["bufferViews"])
        doc["bufferViews"].append({"buffer":0,"byteOffset":len(data),"byteLength":arr.nbytes,"target":34962})
        data.extend(arr.tobytes())
        idx = len(doc["accessors"])
        doc["accessors"].append({"bufferView":view,"componentType":5126,"count":len(arr),"type":"VEC3",
                                 "min":arr.min(axis=0).tolist(),"max":arr.max(axis=0).tolist()})
        return idx
    def vertex_normals(points):
        a,b,c = points[indices].transpose(1,0,2)
        face = np.cross(b-a,c-a)
        result = np.zeros_like(points)
        for column in indices.T:
            np.add.at(result,column,face)
        return result / np.maximum(1.e-12,np.linalg.norm(result,axis=1,keepdims=True))
    p=position*1.85
    x,y,z=p.T
    # The staff remains in the right hand; only the casting hand opens and closes.
    base_normal=vertex_normals(p)
    targets=[]
    for closing in [False,True]:
        delta=np.zeros_like(p)
        for cx,cy,cz,width,length,spread in digits:
            local_y,local_z=y-cy,z-cz
            weight=np.clip(1-((x-cx)/width)**4,0,1)
            weight*=np.clip((z-.44)/.14,0,1)
            depth=np.clip(-local_y/length,0,1)
            weight*=depth*depth*(3-2*depth)
            angle=weight*(1.22 if closing else -.78)
            dz=np.sin(angle)*local_y+(np.cos(angle)-1)*local_z
            dy=(np.cos(angle)-1)*local_y-np.sin(angle)*local_z
            delta[:,1]+=dy
            delta[:,2]+=dz
            delta[:,0]+=weight*spread*(-.34 if closing else .62)
        adjusted=vertex_normals(p+delta)
        change=adjusted-base_normal
        n=normals+change
        n/=np.maximum(1.e-12,np.linalg.norm(n,axis=1,keepdims=True))
        targets.append({"POSITION":write(delta/1.85),"NORMAL":write(n-normals)})
    primitive["targets"]=targets
    doc["meshes"][0]["weights"]=[0,0]
    doc["meshes"][0].setdefault("extras",{})["targetNames"]=["CastOpen","CastClench"]
