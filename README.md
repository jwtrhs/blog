My personal blog.

![deploy status](https://codeberg.org/jwtrhs/blog/badges/workflows/deploy.yaml/badge.svg)

# Generate a PDF CV

```bash
docker run --rm \
       --volume "$(pwd):/data" \
       --user $(id -u):$(id -g) \
       pandoc/latex content/cv.md -o "Jonathon Waterhouse - CV.pdf"
```
