# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/lang/zh-CN/).

## [4.1.0] - 2026-03-21

### 🚀 重构

- **模块化架构重构**: 将 monolithic 的 main.py 拆分为多个职责单一的模块
  - `core/`: 配置管理、语境分析等核心功能
  - `services/`: 表情包服务、群组上下文服务、LLM 服务
  - `handlers/`: 群消息处理器、命令处理器
  - `utils/`: 图片处理、消息处理等工具函数
  - `types.py`: 类型定义
  - `constants.py`: 常量定义

### ✨ 新增

- **语境分析功能**: 基于群聊语境主动发送表情包
  - 滑动窗口机制（默认 30 条消息）
  - 消息计数触发（默认每 5 条消息）
  - 概率判断机制
  - 支持 LLM 智能分析语境
  - 支持关键词匹配作为备选方案

- **QQ 群白名单**: 可配置允许触发表情包的 QQ 群列表

- **LLM 语境分析配置**:
  - 可自定义系统提示词
  - 可自定义用户提示词
  - 支持变量替换（`{emotions_list}`, `{context_text}`）

### 🔧 变更

- **平台限制**: 仅支持 aiocqhttp 适配器（QQ 个人号）
- **插件标识符**: 从 `meme_manager` 改为 `meme_auto`
- **配置结构**: 使用父级分类组织配置（basic、llm_analysis）

### 🗑️ 移除

- 图床相关功能
- gewechat 平台支持
- 原有的 LLM 标签触发表情包逻辑

### 🐛 修复

- 修复 CommandHandler 抽象类实例化问题
- 修复 GroupContextService 构造函数参数问题
- 修复 ContextAnalyzer 构造函数参数问题
- 修复 utils.py 与 utils/ 包命名冲突

## [4.0.0] - 2026-03-20

### 🎉 初始重构版本

- 基于 astrbot_plugin_meme_manager v3.x 重构
- 全新的自动表情包触发机制
