# 数据爬取优化文档

> **最新更新（2025-12-23）**：修复了爬取逻辑问题，解决了"每次显示存在并跳过"的问题。  
> 详细优化内容请查看 [CRAWLER_OPTIMIZATION.md](./CRAWLER_OPTIMIZATION.md)

## 概述

本次优化重新设计了数据爬取和存储流程，采用统一的 `database` 目录结构，每个文档包含：
1. **Markdown 格式原数据**（保留表格、链接等结构）
2. **元数据文件**（JSON 格式）
3. **附件文件**（如有，不解析，原样保存）

---

## 目录结构

```
dataset/
├── database/                    # 统一的文档数据库
│   └── <doc_id>/               # 每个文档一个文件夹
│       ├── content.md          # Markdown 格式原数据
│       ├── meta.json           # 元数据（标题、来源、日期等）
│       └── attachments/        # 附件文件夹（如有）
│           ├── file1.pdf
│           ├── file2.docx
│           └── ...
├── crawl_state.json            # 爬虫状态（已访问的URL）
├── chunks/                     # 分块后的数据（供检索使用）
└── index/                      # FAISS 向量索引
```

### 文档 ID 格式

```
HTU_教务处_通知_YYYY-MM-DD_<数字ID>_<标题前缀>
```

示例：
```
HTU_教务处_通知_2025-11-05_360557_关于开展2026届毕业生毕业图像信息
```

---

## 文件说明

### 1. content.md

Markdown 格式的文档正文，包含：
- **文档标题**（一级标题）
- **元信息**（来源URL、发布日期）
- **分隔线**
- **正文内容**（保留表格、链接、列表等结构）

示例：
```markdown
# 关于组织开展第六届河南省本科高校教师课堂教学创新大赛校级初赛补充遴选的通知

**来源**: https://www.htu.edu.cn/teaching/2025/0331/c3251a340594/page.htm

**发布日期**: 2025-03-31

---

各学院（部）：

根据河南省教育厅办公室《关于举办第六届河南省本科高校教师...
```

### 2. meta.json

文档元数据，JSON 格式：

```json
{
  "doc_id": "HTU_教务处_通知_2025-03-31_340594_关于组织开展第六届河南省本科高校教师",
  "title": "关于组织开展第六届河南省本科高校教师课堂教学创新大赛校级初赛补充遴选的通知",
  "source_url": "https://www.htu.edu.cn/teaching/2025/0331/c3251a340594/page.htm",
  "dept": "教务处",
  "doc_type": "通知公告",
  "publish_date": "2025-03-31",
  "crawl_date": "2025-12-23",
  "lang": "zh",
  "version": "v2",
  "hash_html": "md5:...",
  "has_attachments": true,
  "attachment_count": 2,
  "attachments": [
    {
      "filename": "附件1.pdf",
      "path": "attachments/附件1.pdf",
      "url": "https://www.htu.edu.cn/.../file.pdf",
      "size": 104123,
      "hash": "md5:..."
    }
  ]
}
```

### 3. attachments/ 文件夹

存储文档相关的附件文件（PDF、Word、Excel、ZIP 等），**不进行解析**，原样保存：
- 保留原始文件名
- 如有重名文件，自动添加后缀（_1, _2, ...）
- 支持的附件类型：.pdf, .doc, .docx, .xls, .xlsx, .zip, .rar, .7z, .png, .jpg, .jpeg

---

## 使用说明

### 快速启动（推荐）

#### Windows 用户
直接双击运行：
```
启动爬虫.bat
```
然后选择运行模式：
- [1] 继续爬取（断点续传）
- [2] 强制重新爬取

#### 命令行
```bash
# 继续爬取（断点续传）
python run_crawler.py

# 强制重新爬取
python run_crawler.py --force
```

### 1. 手动运行爬虫

```bash
# 基本用法（继续爬取）
python tools/crawl.py --start "https://www.htu.edu.cn/teaching/3251/list.htm"

# 强制重新爬取
python tools/crawl.py \
  --start "https://www.htu.edu.cn/teaching/3251/list.htm" \
  --force

# 指定输出目录和最大页数
python tools/crawl.py \
  --start "https://www.htu.edu.cn/teaching/3251/list.htm" \
  --out "./dataset" \
  --max-pages 50 \
  --delay 1.0
```

参数说明：
- `--start`: 栏目起始 URL（必需）
- `--out`: 输出根目录（默认：./dataset）
- `--max-pages`: 最多遍历栏目页数（默认：50）
- `--delay`: 请求间隔秒数（默认：1.0）
- `--force`: 强制重新爬取，清除已有状态（可选）

### 2. 测试数据结构

```bash
python tools/test_crawl.py
```

输出示例：
```
✓ 找到 59 篇文档

【文档 1】 HTU_教务处_通知_2025-03-31_340594_关于组织开展第六届河南省本科高校教师
================================================================================
✓ content.md (2373 字符, 106 行)
  前5行预览:
    # 关于组织开展第六届河南省本科高校教师课堂教学创新大赛校级初赛补充遴选的通知
    
    **来源**: https://www.htu.edu.cn/teaching/2025/0331/c3251a340594/page.htm
    ...

✓ meta.json
  - 标题: 关于组织开展第六届河南省本科高校教师课堂教学创新大赛校级初赛补充遴选的通知
  - 发布日期: 2025-03-31
  - 有附件: True
  - 附件数量: 2

✓ attachments/ (2 个文件)
  - 附件1.pdf (101.7 KB)
  - 附件2.docx (33.8 KB)
```

### 3. 数据迁移（从旧结构）

如果你有旧的 `raw/` 和 `staging/` 目录结构：

```bash
python tools/migrate_data.py
```

迁移完成后，可以删除旧目录：
```bash
# PowerShell
Remove-Item -Recurse -Force dataset\raw, dataset\staging

# Linux/Mac
rm -rf dataset/raw dataset/staging
```

### 4. 增强 Markdown 文件

为已存在的 markdown 文件添加标题头部：

```bash
python tools/enhance_markdown.py
```

---

## 优化特性

### ✅ 统一的目录结构
- 不再分散在 `raw/` 和 `staging/`
- 每个文档自包含（Markdown + 元数据 + 附件）
- 便于管理和访问

### ✅ 高质量 Markdown 提取
- 使用 `trafilatura` 提取网页内容
- 保留表格、链接、列表等结构
- 添加标题和元信息头部
- 便于后续文本处理和检索

### ✅ 智能附件处理
- 自动识别并下载附件
- 保留原始文件名
- 处理文件名冲突
- 记录附件元数据（大小、hash、URL）
- **不解析附件内容**，原样保存

### ✅ 增量爬取
- 维护 `crawl_state.json` 记录已访问的 URL
- 避免重复抓取
- 支持断点续爬
- 可手动删除状态文件重新爬取

### ✅ 完善的元数据
- 文档 ID、标题、来源 URL
- 发布日期、爬取日期
- 部门、文档类型、语言
- HTML hash（用于变更检测）
- 附件信息（文件名、路径、大小、hash）

### ✅ 错误处理
- 网络请求失败自动跳过
- 附件下载失败不影响文档保存
- 详细的日志输出
- 友好的错误提示

---

## 技术栈

- **requests**: HTTP 请求
- **BeautifulSoup4**: HTML 解析
- **trafilatura**: 内容提取（保留结构）
- **pathlib**: 路径操作
- **json**: 元数据存储

---

## 注意事项

1. **尊重 robots.txt**：爬取前检查网站的爬虫规则
2. **合理延迟**：默认 1 秒间隔，必要时使用 `--delay` 加大
3. **网络稳定性**：建议在稳定网络环境下运行
4. **附件不解析**：附件保存为原始文件，不提取内容
5. **磁盘空间**：确保有足够空间存储附件

---

## 下一步

爬取完成后，可以进行：
1. **分块处理**：使用 `tools/chunking.py` 将文档分块
2. **构建索引**：使用 `tools/build_index.py` 构建向量索引
3. **RAG 检索**：在应用中使用检索增强生成

---

## 更新日志

### v2.0 (2025-12-23)
- ✅ 统一目录结构为 `database/<doc_id>/`
- ✅ 改进 Markdown 提取质量（保留表格、链接等）
- ✅ 附件存放在同文件夹的 `attachments/` 子目录
- ✅ 添加 Markdown 头部（标题、来源、日期）
- ✅ 完善元数据结构
- ✅ 提供数据迁移和增强脚本

### v1.0
- 基础爬虫功能
- 分离 `raw/` 和 `staging/` 目录
- 基础的附件下载

---

## 联系方式

如有问题或建议，请联系开发团队。

