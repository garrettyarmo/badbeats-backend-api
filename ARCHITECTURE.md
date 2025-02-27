# BadBeats Backend API - Architecture Overview

**Version:** 0.1.0  
**Last Updated:** [Insert Date]

## Purpose

This document provides a comprehensive overview of the repository structure and the flow of data and control in the BadBeats Backend API. It uses a DAG (Directed Acyclic Graph) representation to illustrate how different modules interact and how data flows from ingestion through prediction generation to API serving.

## High-Level Architecture Diagram

Below is a Mermaid diagram that represents the high-level flow of the system:

```mermaid
flowchart TD
    A["External Data Sources"]
    B["NBA API (BallDontLie)"]
    C["News Sources (ESPN, NBA.com, Bleacher Report)"]
    D["Data Ingestion Service"]
    E["Database (PostgreSQL/Supabase)"]
    F["Prediction Models (LangChain LLM)"]
    G["Prediction Scheduling (Celery)"]
    H["API Endpoints (FastAPI)"]
    I["Authentication & Security (JWT/OAuth2)"]
    J["Logging & Monitoring"]
    
    A -->|"Structured & Unstructured Data"| B
    A -->|"News and Injury Reports"| C
    B --> D
    C --> D
    D --> E
    D --> F
    F --> E
    G --> F
    H --> E
    H --> I
    I --> H
    J --> H
    J --> D
    J --> F