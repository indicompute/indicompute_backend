from fastapi import FastAPI

app = FastAPI()

@app.get("/")
def home():
    return {"message": "Welcome to IndiCompute!"}

@app.get("/assign_gpu")
def assign_gpu(user: str, gpu_count: int):
    if gpu_count <= 5:
        return {"status": "success", "message": f"{user}, {gpu_count} GPU assigned!"}
    else:
        return {"status": "failed", "message": f"Sorry {user}, limited GPUs available!"}
