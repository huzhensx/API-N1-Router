#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""API-N1-Router 一键打包脚本

用法（在源码目录下执行）：

    python build.py                 # 同步版本资源 + 打包 exe
    python build.py --version-only  # 只重新生成 version_info.txt，不打包

版本号单一来源：app.py 的 APP_VERSION。
迭代时只需改 app.py 里的 APP_VERSION，本脚本会自动把它同步到：

    ① version_info.txt  —— exe「属性 → 详细信息」里显示的文件版本/产品版本
    ② 最终 exe          —— 由 PyInstaller 通过 --version-file 烧进 PE 资源

产物输出到源码目录的上一级（即 --distpath 指向的目录），不在源码目录生成 dist/。
build/ 与 API-N1-Router.spec 是 PyInstaller 的正常中间产物，留在源码目录。
"""

import argparse
import os
import re
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
APP_PY = os.path.join(HERE, "app.py")
VERSION_FILE = os.path.join(HERE, "version_info.txt")

EXE_NAME = "API-N1-Router"
# 产物输出目录：源码目录的上一级（工作区根）
DIST_DIR = os.path.abspath(os.path.join(HERE, os.pardir))

# ---- exe「详细信息」里的固定字段（想改内容只改这里） ----
COMPANY_NAME = "API-N1-Router"
FILE_DESCRIPTION = "API-N1-Router - 多上游 LLM 智能路由网关"
LEGAL_COPYRIGHT = "Copyright (C) 2026 huzhensx"
LANG_ID = 2052      # 2052 = 中文(简体，中国) -> 属性页「语言」
CODEPAGE = 1200     # 1200 = Unicode

TEMPLATE = """# UTF-8
#
# 本文件由 build.py 自动生成，请勿手工编辑。
# 版本号单一来源：app.py 的 APP_VERSION
VSVersionInfo(
  ffi=FixedFileInfo(
    filevers={quad},
    prodvers={quad},
    mask=0x3f,
    flags=0x0,
    OS=0x40004,
    fileType=0x1,
    subtype=0x0,
    date=(0, 0)
    ),
  kids=[
    StringFileInfo(
      [
      StringTable(
        u'{lang_key}',
        [StringStruct(u'CompanyName', u'{company}'),
        StringStruct(u'FileDescription', u'{desc}'),
        StringStruct(u'FileVersion', u'{ver}'),
        StringStruct(u'InternalName', u'{name}'),
        StringStruct(u'LegalCopyright', u'{copyright}'),
        StringStruct(u'OriginalFilename', u'{exe}'),
        StringStruct(u'ProductName', u'{name}'),
        StringStruct(u'ProductVersion', u'{ver}')])
      ]),
    VarFileInfo([VarStruct(u'Translation', [{lang_id}, {codepage}])])
  ]
)
"""


def read_app_version() -> str:
    with open(APP_PY, encoding="utf-8") as fh:
        src = fh.read()
    m = re.search(r'APP_VERSION\s*=\s*"([^"]+)"', src)
    if not m:
        sys.exit("[x] 未能在 app.py 中找到 APP_VERSION")
    return m.group(1)


def version_quad(ver: str) -> tuple:
    """'1.0.2' -> (1, 0, 2, 0)；不足四位补 0，超过四位截断。"""
    parts = [int(x) for x in re.findall(r"\d+", ver)][:4]
    while len(parts) < 4:
        parts.append(0)
    return tuple(parts)


def write_version_file(ver: str) -> None:
    quad = version_quad(ver)
    text = TEMPLATE.format(
        quad=quad,
        lang_key="{:04X}{:04X}".format(LANG_ID, CODEPAGE),
        company=COMPANY_NAME,
        desc=FILE_DESCRIPTION,
        ver=ver,
        name=EXE_NAME,
        copyright=LEGAL_COPYRIGHT,
        exe=EXE_NAME + ".exe",
        lang_id=LANG_ID,
        codepage=CODEPAGE,
    )
    with open(VERSION_FILE, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(text)
    print("[1/3] 已写入 {}  ->  版本 {}".format(os.path.basename(VERSION_FILE), ver))


def clean_cache() -> None:
    for name in ("build", "dist", EXE_NAME + ".spec"):
        path = os.path.join(HERE, name)
        if os.path.isdir(path):
            shutil.rmtree(path, ignore_errors=True)
            print("[2/3] 已清理目录 {}".format(name))
        elif os.path.exists(path):
            os.remove(path)
            print("[2/3] 已清理文件 {}".format(name))


def build() -> None:
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--noconfirm",
        "--onefile", "--noconsole",
        "--name", EXE_NAME,
        "--icon", "icon.ico",
        "--version-file", "version_info.txt",
        "--distpath", DIST_DIR,
        "--add-data", "templates;templates",
        "--add-data", "models_meta.json;.",
        "--add-data", "icon.ico;.",
        "--hidden-import", "pystray._win32",
        "--hidden-import", "PIL",
        "--hidden-import", "socksio",
        "--exclude-module", "numpy",
        "--exclude-module", "pandas",
        "--exclude-module", "scipy",
        "--exclude-module", "matplotlib",
        "--exclude-module", "PySide6",
        "--exclude-module", "tkinter",
        "--exclude-module", "pytest",
        "--exclude-module", "unittest",
        "app.py",
    ]
    print("[3/3] 开始打包 ...")
    proc = subprocess.run(cmd, cwd=HERE)
    if proc.returncode != 0:
        sys.exit("[x] 打包失败，返回码 {}".format(proc.returncode))
    out = os.path.join(DIST_DIR, EXE_NAME + ".exe")
    if os.path.exists(out):
        print("[ok] 已生成 {}  ({:,} 字节)".format(out, os.path.getsize(out)))
    else:
        sys.exit("[x] 未找到产物 {}".format(out))


def main() -> None:
    ap = argparse.ArgumentParser(description="API-N1-Router 打包脚本")
    ap.add_argument("--version-only", action="store_true",
                    help="只重新生成 version_info.txt，不执行打包")
    args = ap.parse_args()

    ver = read_app_version()
    print("[i] app.py APP_VERSION = {}".format(ver))
    write_version_file(ver)

    if args.version_only:
        print("[ok] 仅同步版本资源，未打包。")
        return

    clean_cache()
    build()


if __name__ == "__main__":
    main()
