### Set Up

`pip3 install load_dotenv`
`pip3 install pymongo`
`pip3 install datetime`

### Schema

#### Device Data

```
name: string

identifier: string

off_code: int[]

on_code: int[]
```

#### Sensor Data

```
sleeping_status: boolean

device_identifier: string

appliance_status: boolean
```
