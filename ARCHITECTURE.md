# BadBeats Backend API - Architecture Overview

**Version:** 0.1.0  
**Last Updated:** 2025-02-27

## Purpose

This document provides a comprehensive overview of the repository structure and the flow of data and control in the BadBeats Backend API. It uses a DAG (Directed Acyclic Graph) representation to illustrate how different modules interact and how data flows from ingestion through prediction generation to API serving.

## High-Level Architecture Diagram

Below is a Mermaid diagram that represents the high-level flow of the system:

```mermaid
flowchart TD
    %% Node definitions with styling
    classDef dataSource fill:#f9d5e5,stroke:#333,stroke-width:1px
    classDef processing fill:#eeeeee,stroke:#333,stroke-width:1px
    classDef storage fill:#b5ead7,stroke:#333,stroke-width:1px
    classDef api fill:#c7ceea,stroke:#333,stroke-width:1px
    classDef security fill:#ff9aa2,stroke:#333,stroke-width:1px
    classDef monitoring fill:#ffdac1,stroke:#333,stroke-width:1px
    
    subgraph External ["External Data Sources"]
        A["NBA API (BallDontLie)"]
        C["News Sources (ESPN, NBA.com)"]
    end
    
    subgraph Core ["Core Processing"]
        D["Data Ingestion Service"]
        F["Prediction Models (LangChain LLM)"]
        G["Prediction Scheduling (Celery)"]
    end
    
    subgraph Storage ["Data Storage"]
        E["Database (PostgreSQL/Supabase)"]
    end
    
    subgraph Interface ["API Layer"]
        H["API Endpoints (FastAPI)"]
        I["Authentication & Security"]
    end
    
    J["Logging & Monitoring"]
    
    %% Connections
    A -->|"Game Stats & Player Data"| D
    C -->|"News and Injury Reports"| D
    D --> E
    D --> F
    F --> E
    G --> F
    H --> E
    H <--> I
    J --> H
    J --> D
    J --> F
    
    %% Apply styles
    class A,C dataSource
    class D,F,G processing
    class E storage
    class H api
    class I security
    class J monitoring
    
    %% Styling for subgraphs
    style External fill:#f9f9f9,stroke:#999,stroke-width:1px
    style Core fill:#f5f5f5,stroke:#999,stroke-width:1px
    style Storage fill:#f0f0f0,stroke:#999,stroke-width:1px
    style Interface fill:#f7f7f7,stroke:#999,stroke-width:1px