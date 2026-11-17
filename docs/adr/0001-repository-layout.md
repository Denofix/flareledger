# Repository layout and integration branch

Status: accepted for the initial repository bootstrap, 2026-11-14.

The project uses one repository with backend/, frontend/, data/, infra/, scripts/, docs/, design/, and presentation/. The backend and frontend own their dependencies independently. No extra monorepo framework is introduced at this stage.

main is the integration branch. Contributors use short-lived task branches and pull requests. The first repository bootstrap is written directly into the previously empty main branch.

This keeps the application contract visible to software developers, the designer, and the infrastructure owner. Application build checks are added with actual source code and dependency files. Repository metadata checks are available from the bootstrap.

The purchased domain is flareledger.fun. It replaces the earlier free-subdomain plan. Hosting remains a separate decision, with QResto reuse subject to inspection and Vercel frontend hosting available as an alternative.
