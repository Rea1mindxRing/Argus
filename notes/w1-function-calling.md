# Agent Runtime 第一课 · Function Calling 协议笔记

## 主题 1：请求结构
- **核心事实**
  - messages 是"会呼吸的"纯文本序列,模型整体读它预测下一个 token。
  - system 只是最前一段指令文本,不是"权限消息";作用强度由**位置**决定。
  - 越靠后/越贴近任务的文本,覆盖力越强 → 位置即优先级,role 只是语义标签。
  - 顺序:通常 system 后跟对话(user/assistant/tool 交替),四条 role 语义各异。
- **我答错的地方**
  - 把 system 理解成"系统级约束/权限高"。纠正:它是序列首位的一段指令,靠前置生效,非级别高。
- **一句话总结**
  - system 是最前的一段文本指令,不是特权消息;messages 是连续文本,位置即优先级。

## 主题 2：工具的序列化
- **核心事实**
  - tools 四字段归属:
    - `type` → runtime/平台,声明这是什么工具。
    - `function.name` → 模型**选**工具 + 执行器**分发**工具(要全局唯一稳定)。
    - `function.description` → 主要给模型,决定何时用、怎么填参。
    - `function.parameters` → **两边都用**:模型按它**生成** arguments,执行器按它**校验** arguments。
  - 执行器是"核对方"不是"替章方":schema 没写 default,缺 key 就是没传,不脑补默认值。
  - 执行器内部(函数签名)自己处理缺省,而非调度层按 schema 补。
- **我答错的地方**
  - 只说"parameters 给执行器用"。纠正:它是给模型生成 + 给执行器校验的双面工具,模型侧更重要。
- **一句话总结**
  - parameters 是同一 schema 的两面:模型改编造 args,执行器核 args;执行器绝不替模型补默认值。

## 主题 3：响应的解读
- **核心事实**
  - finish_reason 是调度分叉开关:
    - `tool_calls` → 先别回答,去干活并继续循环(`content` 常空,关键在 `message.tool_calls`)。
    - `stop` → 讲完了,把 content 返回,循环结束。
    - `length` → 被截断(主题 5)。
  - tool_calls 数组 = 模型想一次调的多个工具;每个含 id / type / function.name / function.arguments。
  - runtime 拍板逻辑:`if finish_reason=="tool_calls": 执行工具 else: 返回 content`。
- **我答错的地方**
  - 这段我较迷糊;核心要抓住"tool_calls 是继续信号,stop 才是终点"。
- **一句话总结**
  - finish_reason 是分叉开关:tool_calls=去干活并循环,stop=收尾结束;跑几圈取决于何时从 tool_calls 换到 stop。

## 主题 4：结果的回填
- **核心事实**
  - 模型开几张 tool_call"工单",就回填几条 `role="tool"` 的"带回执",必须**紧跟在那条 assistant 之后**,再整体发回。
  - 每条 tool 消息的 `tool_call_id` 填它对应的那张工单号,一一对账是铁律(多工具下贴错会串账)。
  - 结果必须走 `tool` 通道,不能塞 user:
    - 只有 tool 带 tool_call_id,能精确对回工单。
    - 塞 user 会把系统输出伪装成"用户权威",既对不上账,又制造注入面。
- **我答错的地方**
  - 当时处在本课最卡的点;请重点记忆"工单 vs 回执"的对账模型。
- **一句话总结**
  - 一 tool_calls 对应几条带上对应 tool_call_id 的 tool 回执,紧跟其 assistant 后;结果必走 tool 通道以对账并避免伪造用户身份。

## 主题 5：边界情况
- **核心事实**
  - `arguments` 是 JSON 字符串,执行前必 `json.loads`;可能为空(`""` 非法、`"{}"` 合法)或坏 JSON;
    解析失败/为空一律不执行,回填一条 `tool` 错误消息让模型自愈重试。
  - `max_tokens` 耗尽 → `finish_reason="length"`,是**异常截断**信号,不是成功结束:
    - 残缺 tool_call 不执行,当错误处理(回填错误/精简重发),而非无脑追加。
    - 真正防死循环的是带`tool_call_id`配对 + 全局 **max_iters** 兜底。
  - 完整三轮时序(system → user → assistant[2 calls] → tool×2 → assistant[1 call] → tool → assistant[stop])。
- **我答错的地方**
  - ❌ 第 5 题答成 "stop,终止"。纠正:**max_tokens 耗尽是 length,不是 stop;length 当异常处理,stop 才是合法终止,用 max_iters 兜底防死循环。**
- **一句话总结**
  - arguments 需解析且可能为空/坏掉,失败就回填错误自愈;length 是被截断的异常而非终止,用 max_iters 防死循环,直到无 tool_calls 的 stop 才真正结束。

---

> 本轮快问快答:4/5 对,唯一修正是"length ≠ stop,length 表示异常截断"。整体合格。