# Infrastructure

Timofey coordinates the infrastructure implementation. The first infrastructure PR should use the merged backend and frontend files, actual dependency commands, explicit state paths, and the selected ingress route.

Dockerfiles, Compose, deployment scripts, and application build jobs are not implemented in this bootstrap. Follow [the technical contract](../docs/TECHNICAL_CONTRACT.md) and [deployment decision](../docs/DEPLOYMENT.md).

For QResto reuse, confirm existing services and 80/443 ownership before changing routing. Use isolated FlareLedger state and service names. The purchased domain is flareledger.fun; the target server IP remains unconfirmed.
