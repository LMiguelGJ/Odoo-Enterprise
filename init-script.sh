#!/bin/bash

# Variables de la base de datos
db_user="postgres"  # Usar el usuario 'postgres' de PostgreSQL
db_name="CPS"

# Detener el servicio de Odoo
echo "Deteniendo el servicio Odoo..."
sudo systemctl stop odoo16.service

# Función para ejecutar comandos SQL con reintentos
execute_sql_with_retries() {
  local max_retries=5
  local retry_interval=10
  local attempt=1

  while [ $attempt -le $max_retries ]
  do
    echo "Intento $attempt de $max_retries para ejecutar comandos SQL en la base de datos..."

    # Ejecutar como el usuario 'postgres' sin necesidad de contraseña
    if sudo -u postgres psql -d ${db_name} -f /init-db.sql; then
      echo "Comandos SQL ejecutados con éxito."
      return 0
    else
      echo "Error al ejecutar comandos SQL. Intentando de nuevo en $retry_interval segundos..."
      sleep $retry_interval
      attempt=$((attempt + 1))
    fi
  done

  echo "Falló la ejecución de comandos SQL después de $max_retries intentos."
  return 1
}

# Ejecutar comandos SQL en la base de datos con reintentos
echo "Ejecutando comandos SQL en la base de datos..."
execute_sql_with_retries

# Esperar 5 segundos antes de reiniciar Odoo
sleep 5

# Iniciar el servicio de Odoo
echo "Iniciando el servicio Odoo..."
sudo systemctl start odoo16.service

echo "Proceso completado."
