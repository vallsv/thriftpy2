struct Data {
    1: i32 size
    2: binary data
}

service ComputeService {
    void ping();
    Data echo(1: Data data);
    i32 size(1: Data data);
}
