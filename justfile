cv:
  docker run --rm --volume "$(pwd):/data" --user $(id -u):$(id -g) pandoc/latex content/cv.md -o "Jonathon Waterhouse - CV.pdf"
