#!/bin/bash
# delete_all_data_in_redis_docker.sh

echo "Deleting all data in Redis Docker container..."
docker exec -it algo-redis redis-cli FLUSHALL
echo "All data deleted."