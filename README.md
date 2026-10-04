# Python Hello

The most basic boilerplate to start a Python project at 4Geeks is to start your very first Python project from scratch.

## What to do next?

Open the `main.py` file and start writing your code.

Execute your code by typing the following command on your terminal:

```bash
$ python main.py
```

You can create and include as many python files (a.k.a. modules) as you want using the import statements.

## Inventario Suministros Carla

Este proyecto incluye un agente de inventario con interfaz web. Para arrancarlo necesitas **dos procesos** corriendo al mismo tiempo:

**Terminal 1 — API (FastAPI)**
```bash
uvicorn api.app:app --reload
```

**Terminal 2 — Servidor web + agente (Flask)**
```bash
python server.py
```

Luego abre `http://localhost:3000` en tu navegador.

> Asegúrate de tener un archivo `.env` con tu `GROQ_API_KEY` antes de arrancar.

## Requirements

Make sure you have Python installed in your computer. We strongly recommend [installing Python through Pyenv ](https://4geeks.com/how-to/what-is-pyenv-and-how-to-install-pyenv) to avoid version conflicts in the future.

### Contributors

This template was built as part of the [4Geeks Python Resources](https://4geeks.com/technology/python) for learning at [4Geeks.com](https://4geeks.com) by [Alejandro Sanchez](https://twitter.com/alesanchezr) and [many other contributors](https://github.com/4GeeksAcademy/python-hello/graphs/contributors).
