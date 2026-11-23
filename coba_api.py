from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import aturan


class IsiCatatan(BaseModel):
    isi: str

class MintaSelesai(BaseModel):
    id: int

app = FastAPI()
catatan = []

@app.get("/perangkat")
def daftar():
    return aturan.DEVICES

@app.get("/sapaan")
def sapaan(nama: str = "tamu"):
    return {"teks": f"Halo {nama}"}

@app.post("/catatan")
def tambah(data: IsiCatatan):
    if not data.isi.strip():
        raise HTTPException(status_code=400, detail="isi kosong")
    nomor = len(catatan) + 1
    catatan.append({"id": nomor, "isi": data.isi.strip()})
    return catatan[-1]


@app.post("/catatan/selesai")
def selesai(data: MintaSelesai):
    for item in catatan:
        if item["id"] == data.id:
            return {"berhasil": True, "catatan": item}
    raise HTTPException(status_code=404, detail="catatan tidak ada")