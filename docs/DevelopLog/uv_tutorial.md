`uv init` 命令是开始一个新 `uv` 项目的关键第一步，它会为你设置好基础结构。
 **初始化 `uv` 项目:**
    进入到你的项目目录后，运行 `uv init` 命令。

    ```bash
    uv init
    ```

**初始化后的下一步：**

初始化完成后，你的项目目录现在应该看起来像这样（或类似）：

```
my-uv-project/
├── .python-version
├── pyproject.toml
├── README.md
└── main.py
```

**添加项目依赖:**
    使用 `uv add` 命令来添加你的项目所需的库。这会自动更新 `pyproject.toml` 文件，并在下次 `uv sync` 或 `uv run` 时安装这些依赖。

    ```bash
    uv add requests # 添加 requests 库
    uv add numpy pandas # 添加多个库
    uv add --dev pytest ruff # 添加开发依赖
    ```
**运行你的项目脚本:**
    你可以使用 `uv run` 命令来运行你的 Python 脚本。`uv run` 会在运行脚本前自动确保环境是最新的（包括创建虚拟环境和同步依赖）。

    ```bash
    uv run main.py
    ```

 `uv` 环境复刻的简要步骤：

---

## 共享项目（你的操作）

1.  **提交关键文件**：确保你的 Git 仓库中包含 **`pyproject.toml`** (定义直接依赖) 和 **`uv.lock`** (锁定所有精确依赖版本)。
2.  **忽略虚拟环境**：在 `.gitignore` 中加入 `.venv/`，不要将虚拟环境提交到 Git。

---

## 复刻环境（他人的操作）

1.  **安装 `uv`**：如果还没安装，先安装 `uv`。
    * `curl -LsSf https://astral.sh/uv/install.sh | sh` (macOS/Linux)
    * `powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"` (Windows)

2.  **进入项目目录**：`cd your-project-name`

3.  **同步环境**：运行 `uv sync`。这将根据 `uv.lock` 文件自动创建 `.venv` 虚拟环境并安装所有精确版本的依赖。

4.  **运行项目**：使用 `uv run your_script.py` 或 `uv run pytest` 等命令执行项目操作。

---

通过 `uv.lock` 文件，`uv` 能确保在任何机器上都能重建出完全一致的项目环境。