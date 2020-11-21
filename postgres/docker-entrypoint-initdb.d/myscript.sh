#!/bin/bash
psql -U postgres -c "CREATE USER postgres PASSWORD 'postgres'"
psql -U postgres -c "CREATE DATABASE postgres OWNER postgres"