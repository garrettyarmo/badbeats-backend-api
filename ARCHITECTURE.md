# BadBeats Backend API - Architecture Overview

**Version:** 0.1.0  
**Last Updated:** 02/27/2025

## Purpose

This document provides a comprehensive overview of the repository structure and the flow of data and control in the BadBeats Backend API. It uses a detailed Directed Acyclic Graph (DAG) representation to illustrate how different modules interact and how data flows from external sources through ingestion and prediction generation, then to API serving and finally to the front end.

## High-Level Architecture Diagram

Below is the detailed Mermaid diagram that represents the overall project architecture:

```mermaid
flowchart TD
    %% External Data Sources
    subgraph ExternalSources["External Data Sources"]
      A1["NBA API (BallDontLie)"]
      A2["News Sources (ESPN, NBA.com, Bleacher Report)"]
    end

    %% Data Ingestion & Processing
    subgraph Ingestion["Data Ingestion & Processing"]
      B1["Structured Data Processing"]
      B2["Unstructured Data Processing"]
    end

    %% Database Storage
    subgraph Storage["Database (PostgreSQL/Supabase)"]
      C["Stored Data & Predictions"]
    end

    %% Prediction Engine
    subgraph Prediction["Prediction Engine"]
      D["LangChain Prediction Model (LLM)"]
    end

    %% Task Scheduler & Workers
    subgraph Scheduler["Task Scheduler (Celery + Redis)"]
      E["Schedule & Execute Tasks"]
    end

    %% API Endpoints & Security
    subgraph API["API Layer (FastAPI)"]
      F["RESTful Endpoints"]
      G["Authentication (JWT/OAuth2)"]
    end

    %% Logging & Monitoring
    subgraph Monitoring["Logging & Monitoring"]
      H["Centralized Logging & Error Handling"]
    end

    %% Frontend Client
    subgraph FrontEnd["Frontend Application"]
      I["Web Client"]
    end

    %% Data Flow Connections
    A1 -->|"Structured Data"| B1
    A2 -->|"News & Injury Reports"| B2
    B1 -->|"Processed Stats"| C
    B2 -->|"Processed News"| C
    C -->|"Data for Predictions"| D
    E -->|"Triggers Predictions"| D
    D -->|"Generated Predictions"| C
    F -->|"Read/Write Data"| C
    G -->|"Secures Endpoints"| F
    H -->|"Logs"| B1
    H -->|"Logs"| B2
    H -->|"Logs"| D
    H -->|"Logs"| F
    I -->|"HTTP Requests"| F
    E -->|"Schedules Tasks"| D
```