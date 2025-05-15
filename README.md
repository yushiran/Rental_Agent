# The AI Lawyer: Transforming Contract Negotiation with Intelligent Agentic Systems

**Prof Miguel Rodrigues [UCL Engineering]**  
**Prof Carsten Gerner-Beuerle [UCL Law]**

## Overview

This project focuses on harnessing AI agentic systems to automate and optimize contract negotiation workflows, with a particular emphasis on loan agreements.

It leverages advanced frameworks like Microsoft's AutoGen to design, implement, and evaluate a fully autonomous, multi-agent system capable of negotiating contracts on behalf of opposing parties.


| Project Name | Language | Best For | Strengths | Drawbacks |
|--------------|----------|----------|-----------|-----------|
| **LangChain** | Python, JS (limited) | Developers building custom LLM apps | Modular design, tons of integrations, multi-step workflows, agent/memory/tool chaining | Complex workflows require solid understanding of prompts & LLM behavior; API evolves rapidly |
| **LangGraph** | Python | Stateful, graph-based agent workflows | Graph-based control flow, retries, branches, loops; deep LangChain integration | Requires graph & LangChain understanding; still evolving |
| **AutoGen** (Microsoft) | Python | Multi-agent systems, code automation | Conversation-based coordination, built-in agents, code gen & retry, GUI prototyping | Risk of infinite loops if poorly constrained; careful prompt & logic design required |
| **Semantic Kernel** | Python, C#, Java | Embedding AI into enterprise apps/copilots | Lightweight plugin model, skill/planner separation, enterprise-ready | Lacks high-level agent orchestration found in LangChain |
| **OpenAI Agents SDK** (Swarm) | Python | Lightweight, production-ready autonomous agents | Fast, minimal, structured with tools/guardrails, function-calling optimized | Tied to OpenAI models, smaller community |
| **SuperAGI** | Python | Persistent agents with observability/UI | Multi-agent management, vector memory, tool/plugin marketplace, web UI | Heavy infra setup (Docker, Redis, DB) |
| **CrewAI** | Python | Role-based agent collaboration | Agent roles (Planner/Coder/etc.), structured pipelines, LangChain compatible | Sequential only; limited parallelism; newer ecosystem |


![AI Lawyer System Architecture](https://github.com/yushiran/picx-images-hosting/raw/master/ai_lawyer/ai_lawyer.drawio.83a9hgwepi.svg)

![AI Lawyer RAG System Architecture](https://github.com/yushiran/picx-images-hosting/raw/master/ai_lawyer/ai_lawyer_ragsystem.drawio.svg)

