# Bib image for Ensimag workshop

Build image: `docker build . -t workshop_ensimag:latest`

Go to the parent dir of the "ansible_workshop" clone
Start container: `docker run -d --rm --name ansible_test -p 3000:3000 -p 3001:3001 -v ./ansible_workshop:/ansible -v ./front-end-car:/front -v ./back-end-car:/back workshop_ensimag:latest`

Obtain a shell in container: `docker exec -it ansible_test /bin/bash`

Kill container: `docker kill ansible_test`
