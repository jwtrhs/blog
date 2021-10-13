job "blog" {
    datacenters = ["home1"]

    group "main" {

        network {
            port "blog" {
                static = 8888
            }
        }

        task "blog" {
            driver = "docker"

            config {
                image = "https://registry.wtrhs.com/wtrhs/blog:latest"
                labels { group = "registry" }

                auth {
                    username = "registry"
                    password = "3F9UD2Eq"
                }

                ports = ["blog"]
            }

            service {
                name = "${TASK}"
                tags = [ "public" ]

                address_mode = "host"
                port = "blog"
                check {
                    type        = "tcp"
                    port        = "blog"
                    interval    = "10s"
                    timeout     = "3s"
                }
            }
        }
    }
}